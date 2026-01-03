-- DWCOA Financial Tracker Categorization Rules
-- Pattern matching rules for auto-categorization

-- Clear existing rules (for clean re-initialization)
DELETE FROM categorize_rules;

-- Utility company patterns (high confidence)
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'WASHINGTON.*ALARM', id, 95, 100 FROM categories WHERE name = 'Fire Alarm';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'SEATTLE.*CITY.*LIGHT|SEATTLEUTILITIES|SCL', id, 95, 100 FROM categories WHERE name = 'Seattle City Light';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'CINTAS', id, 95, 100 FROM categories WHERE name = 'Cintas Fire Protection';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'NWEDI.*EDI|NWEDI-291390275', id, 90, 90 FROM categories WHERE name = 'Insurance Premiums';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'BULGER', id, 95, 100 FROM categories WHERE name = 'Bulger Safe & Lock';

-- Interest income pattern
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'Dividend.*Interest|DIVIDEND.*INTEREST', id, 98, 100 FROM categories WHERE name = 'Interest income';

-- Internal transfer patterns
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'Internet Transfer|Reserve Funds|Transfer to|Transfer from', id, 95, 100 FROM categories WHERE name = 'Transfers';

-- Dues by owner name patterns (from training data analysis)
-- Unit 101 - WENLU CHENG
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'WENLU CHENG|WENLU.*CHENG', id, 92, 80 FROM categories WHERE name = 'Dues 101';

-- Unit 102 - Emma Landsman
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'Emma Landsman|EMMA.*LANDSMAN|LANDSMAN', id, 92, 80 FROM categories WHERE name = 'Dues 102';

-- Unit 103 - Boeing Employees Credit Union (specific pattern)
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'BOEING EMPLOYEES.*CREDIT UNION.*ELS', id, 85, 70 FROM categories WHERE name = 'Dues 103';

-- Unit 201 - R Young
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'R Young|R.*YOUNG.*ACH', id, 92, 80 FROM categories WHERE name = 'Dues 201';

-- Unit 203 - EVE HWANG
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'EVE HWANG|EVE.*HWANG', id, 92, 80 FROM categories WHERE name = 'Dues 203';

-- Unit 301 - JARED MOLTON
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'JARED MOLTON|JARED.*MOLTON', id, 92, 80 FROM categories WHERE name = 'Dues 301';

-- Unit 302 - J ERNAST
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'J ERNAST|J.*ERNAST|ERNAST', id, 92, 80 FROM categories WHERE name = 'Dues 302';

-- Landscaping/Grounds patterns
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'LANDSCAP|GARDEN|LAWN|GROUNDS', id, 85, 70 FROM categories WHERE name = 'Grounds/Landscaping';

-- Cleaning patterns
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'CLEAN|JANITORIAL|MAID', id, 85, 70 FROM categories WHERE name = 'Common Area Cleaning';

-- Generic deposit pattern (low confidence, will need review)
INSERT INTO categorize_rules (pattern, category_id, confidence, priority)
SELECT 'External Deposit|Deposit', id, 50, 10 FROM categories WHERE name = 'Other';
