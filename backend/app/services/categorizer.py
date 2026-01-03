"""Auto-categorization service using rules engine and Claude API."""

import json
import os
import re
from typing import List, Optional, Tuple

from aws_lambda_powertools import Logger

from app.services import database
from app.models.entities import CategorizationResult


# Initialize structured logger
logger = Logger(service="dwcoa-categorizer")

# Confidence threshold for marking as needs_review
REVIEW_THRESHOLD = 80


def categorize_transaction(description: str, account_name: str) -> CategorizationResult:
    """Categorize a single transaction using rules engine.

    Args:
        description: Transaction description
        account_name: Account name (Savings, Checking, Reserve Fund)

    Returns:
        CategorizationResult with category and confidence
    """
    # Try rules engine first
    rules = database.get_categorize_rules()

    for rule in rules:
        try:
            pattern = rule['pattern']
            if re.search(pattern, description, re.IGNORECASE):
                logger.info(
                    "Rules engine match",
                    extra={
                        "categorization_source": "rules_engine",
                        "pattern_matched": pattern,
                        "category_id": rule['category_id'],
                        "category_name": rule['category_name'],
                        "confidence": rule['confidence'],
                        "description_preview": description[:50],
                        "account": account_name
                    }
                )
                return CategorizationResult(
                    category_id=rule['category_id'],
                    category_name=rule['category_name'],
                    confidence=rule['confidence'],
                    needs_review=rule['confidence'] < REVIEW_THRESHOLD,
                    source='rule'
                )
        except re.error:
            # Invalid regex pattern, skip
            logger.warning(
                "Invalid regex pattern in rules",
                extra={"pattern": rule['pattern'], "rule_id": rule.get('id')}
            )
            continue

    # No rule matched
    logger.debug(
        "No rules engine match",
        extra={
            "categorization_source": "none",
            "description_preview": description[:50],
            "account": account_name
        }
    )
    return CategorizationResult(
        category_id=None,
        category_name=None,
        confidence=0,
        needs_review=True,
        source='none'
    )


def categorize_batch_with_claude(
    transactions: List[dict],
    categories: List[dict]
) -> List[CategorizationResult]:
    """Categorize multiple transactions using Claude API.

    Args:
        transactions: List of transaction dicts with 'description' and 'account_name'
        categories: List of available category dicts

    Returns:
        List of CategorizationResult for each transaction
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')

    if not api_key:
        logger.warning(
            "Claude API key not configured",
            extra={"transaction_count": len(transactions)}
        )
        return [
            CategorizationResult(
                category_id=None,
                category_name=None,
                confidence=0,
                needs_review=True,
                source='none'
            )
            for _ in transactions
        ]

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Build category list for prompt
        category_list = "\n".join([
            f"- {c['name']} ({c['type']})"
            for c in categories
            if c.get('active', True)
        ])

        # Build transaction list for prompt
        txn_list = "\n".join([
            f"{i+1}. Account: {t['account_name']}, Description: {t['description']}"
            for i, t in enumerate(transactions)
        ])

        prompt = f"""You are a financial transaction categorizer for a condo association.
Given the following categories:
{category_list}

Categorize each of these transactions. For each, provide:
1. The category name (exactly as listed above)
2. A confidence score from 0-100

Transactions to categorize:
{txn_list}

Respond in JSON format:
[
  {{"index": 1, "category": "Category Name", "confidence": 85}},
  ...
]

Rules:
- "Dues XXX" categories are for payments from unit owners (look for names in description)
- "Transfers" is for internal transfers between accounts (Internet Transfer, Reserve Funds)
- "Interest income" is for Dividend/Interest entries
- If truly uncertain, use "Other" with low confidence
"""

        logger.info(
            "Calling Claude API for categorization",
            extra={
                "categorization_source": "claude_api",
                "transaction_count": len(transactions),
                "model": "claude-3-haiku-20240307"
            }
        )

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = message.content[0].text

        # Extract JSON from response
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            raise ValueError("No JSON array found in response")

        results_json = json.loads(json_match.group())

        # Map category names to IDs
        category_map = {c['name']: c['id'] for c in categories}

        results = []
        for i, txn in enumerate(transactions):
            # Find matching result
            result_data = next(
                (r for r in results_json if r.get('index') == i + 1),
                None
            )

            if result_data:
                cat_name = result_data.get('category', '')
                confidence = result_data.get('confidence', 0)
                cat_id = category_map.get(cat_name)

                logger.info(
                    "Claude API categorization",
                    extra={
                        "categorization_source": "claude_api",
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "confidence": confidence,
                        "description_preview": txn['description'][:50],
                        "account": txn['account_name']
                    }
                )

                results.append(CategorizationResult(
                    category_id=cat_id,
                    category_name=cat_name if cat_id else None,
                    confidence=confidence,
                    needs_review=confidence < REVIEW_THRESHOLD or cat_id is None,
                    source='claude'
                ))
            else:
                results.append(CategorizationResult(
                    category_id=None,
                    category_name=None,
                    confidence=0,
                    needs_review=True,
                    source='none'
                ))

        logger.info(
            "Claude API batch complete",
            extra={
                "categorization_source": "claude_api",
                "transaction_count": len(transactions),
                "successful_count": sum(1 for r in results if r.category_id is not None)
            }
        )

        return results

    except Exception as e:
        logger.error(
            "Claude API error",
            extra={
                "error": str(e),
                "transaction_count": len(transactions)
            }
        )
        # Return uncategorized on error
        return [
            CategorizationResult(
                category_id=None,
                category_name=None,
                confidence=0,
                needs_review=True,
                source='none'
            )
            for _ in transactions
        ]


def categorize_transactions(transactions: List[dict]) -> List[Tuple[dict, CategorizationResult]]:
    """Categorize a list of transactions.

    First tries rules engine, then batches remaining for Claude API.

    Args:
        transactions: List of transaction dicts

    Returns:
        List of (transaction, result) tuples
    """
    results: List[Tuple[dict, CategorizationResult]] = []
    uncertain: List[Tuple[int, dict]] = []  # (index, transaction)

    rules_matched = 0
    rules_low_confidence = 0

    # First pass: rules engine
    for i, txn in enumerate(transactions):
        result = categorize_transaction(
            txn['description'],
            txn['account_name']
        )

        if result.category_id is not None and result.confidence >= REVIEW_THRESHOLD:
            # High confidence match
            results.append((txn, result))
            rules_matched += 1
        else:
            # Need Claude API
            uncertain.append((i, txn))
            results.append((txn, result))  # Placeholder
            if result.category_id is not None:
                rules_low_confidence += 1

    # Second pass: Claude API for uncertain transactions
    claude_improved = 0
    if uncertain:
        categories = database.get_categories(active_only=True)
        uncertain_txns = [t for _, t in uncertain]

        claude_results = categorize_batch_with_claude(uncertain_txns, categories)

        # Update results with Claude's categorizations
        for (orig_idx, _), claude_result in zip(uncertain, claude_results):
            # Only use Claude result if better than rules
            current = results[orig_idx][1]
            if claude_result.confidence > current.confidence:
                results[orig_idx] = (results[orig_idx][0], claude_result)
                claude_improved += 1

    # Log batch summary
    logger.info(
        "Categorization batch summary",
        extra={
            "total_transactions": len(transactions),
            "rules_engine_matched": rules_matched,
            "rules_low_confidence": rules_low_confidence,
            "sent_to_claude": len(uncertain),
            "claude_improved": claude_improved,
            "uncategorized": len(transactions) - rules_matched - claude_improved
        }
    )

    return results


def extract_pattern_from_description(description: str) -> list[str]:
    """Extract meaningful patterns from a transaction description.

    Returns multiple candidate patterns, from most specific to least.

    Args:
        description: Transaction description

    Returns:
        List of regex patterns to try
    """
    patterns = []

    # Clean up description
    desc = description.strip()

    # Skip common prefixes that aren't distinctive
    skip_prefixes = [
        'External Deposit', 'Deposit', 'Withdrawal', 'Payment',
        'Descriptive Deposit', 'Business Mobile Deposit',
        'Incoming Wire Transfer', 'ACH', 'CREDIT', 'DEBIT'
    ]

    # Try to find the distinctive part (usually a name or company)
    remaining = desc
    for prefix in skip_prefixes:
        if remaining.upper().startswith(prefix.upper()):
            remaining = remaining[len(prefix):].strip()
            # Remove common separators
            remaining = remaining.lstrip('- ').strip()

    # Extract potential name patterns (capitalized words, often sender names)
    # Look for patterns like "JOHN DOE" or "J SMITH" or "Company Name"
    words = remaining.split()

    # Pattern 1: If we have a clean name/identifier after removing prefixes
    if remaining and len(remaining) >= 3:
        # Use the cleaned identifier (escape for regex)
        patterns.append(re.escape(remaining.split()[0]) if words else re.escape(remaining[:20]))

    # Pattern 2: Look for name patterns (2-3 capitalized words)
    name_words = []
    for word in words[:4]:  # Check first 4 words
        # Skip common transaction words
        if word.upper() in ['ONLNE', 'TRNSFR', 'ACH', 'TRANSFER', 'SENDER', 'CREDIT', 'P2P', 'XFR']:
            continue
        # Keep likely name parts
        if len(word) >= 2 and word[0].isupper():
            name_words.append(word)
        if len(name_words) >= 2:
            break

    if len(name_words) >= 2:
        # Create pattern from name words
        pattern = '.*'.join(re.escape(w) for w in name_words)
        patterns.append(pattern)
    elif name_words:
        patterns.append(re.escape(name_words[0]))

    # Pattern 3: Original description's first distinctive word
    for word in desc.split():
        if len(word) >= 4 and word.upper() not in ['DEPOSIT', 'EXTERNAL', 'PAYMENT', 'WITHDRAWAL']:
            patterns.append(re.escape(word))
            break

    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for p in patterns:
        if p not in seen and len(p) >= 3:
            seen.add(p)
            unique_patterns.append(p)

    return unique_patterns[:3]  # Return top 3 patterns


def learn_pattern(description: str, category_id: int, confidence: int = 90) -> None:
    """Learn a new categorization pattern from manual categorization.

    Extracts meaningful patterns from the description and saves them as rules.
    Future transactions matching these patterns will be auto-categorized.

    Args:
        description: Transaction description
        category_id: Category ID assigned
        confidence: Confidence for new rule
    """
    patterns = extract_pattern_from_description(description)

    if not patterns:
        logger.warning(
            "Pattern learning failed - no patterns extracted",
            extra={
                "description_preview": description[:50],
                "category_id": category_id
            }
        )
        return

    # Use the first (most specific) pattern
    pattern = patterns[0]

    # Get category name for logging
    cat = database.get_category_by_id(category_id)
    cat_name = cat['name'] if cat else f'ID:{category_id}'

    # Check if similar rule exists for this category
    existing = database.fetch_one(
        "SELECT id, pattern FROM categorize_rules WHERE pattern = ? AND category_id = ?",
        (pattern, category_id)
    )

    if existing:
        # Update confidence if higher
        database.execute(
            "UPDATE categorize_rules SET confidence = MAX(confidence, ?) WHERE id = ?",
            (confidence, existing['id'])
        )
        logger.info(
            "Pattern learning - updated existing rule",
            extra={
                "pattern_learning": True,
                "action": "update",
                "pattern": pattern,
                "category_id": category_id,
                "category_name": cat_name,
                "confidence": confidence,
                "rule_id": existing['id'],
                "description_preview": description[:50]
            }
        )
    else:
        # Create new rule with lower priority (learned rules)
        database.execute(
            """INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
               VALUES (?, ?, ?, 50)""",
            (pattern, category_id, confidence)
        )
        logger.info(
            "Pattern learning - created new rule",
            extra={
                "pattern_learning": True,
                "action": "create",
                "pattern": pattern,
                "category_id": category_id,
                "category_name": cat_name,
                "confidence": confidence,
                "priority": 50,
                "description_preview": description[:50]
            }
        )
