from utils import (
    LEVEL_ONE_MEDICAL_RESPONSES,
    LEVEL_TWO_MEDICAL_RESPONSES,
    LEVEL_ONE_LEGAL_RESPONSES,
    LEVEL_TWO_LEGAL_RESPONSES,
    LEVEL_ONE_FINANCIAL_RESPONSES,
    LEVEL_TWO_FINANCIAL_RESPONSES,
    LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES,
    LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
    INTRO_PROMPTS
)

rulebook = [
    {
        "confidence": "high",
        "conditions": ["CookingDomain"],
        "response": "[REDIRECT]"
    },
    {
        "confidence": "high",
        "conditions": ["DIYDomain"],
        "response": "[REDIRECT]"
    },
    {
        "confidence": "high",
        "conditions": ["MedicalDomain"],
        "response": {
            0: LEVEL_ONE_MEDICAL_RESPONSES,
            # level 1
            1: LEVEL_ONE_MEDICAL_RESPONSES,
            2: LEVEL_TWO_MEDICAL_RESPONSES
        }
    },
    {
        "confidence": "high",
        "conditions": ["FinancialDomain"],
        "response": {
            0: LEVEL_ONE_FINANCIAL_RESPONSES,
            1: LEVEL_ONE_FINANCIAL_RESPONSES,
            2: LEVEL_TWO_FINANCIAL_RESPONSES
        }
    },
    {
        "confidence": "high",
        "conditions": ["LegalDomain"],
        "response": {
            0: LEVEL_ONE_LEGAL_RESPONSES,
            1: LEVEL_ONE_LEGAL_RESPONSES,
            2: LEVEL_TWO_LEGAL_RESPONSES
        }
    },
    {
        "confidence": "high",
        "conditions": ["UndefinedDomain"],
        "response": {
            # level 0 because it is the intro
            0: INTRO_PROMPTS,
            1: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            2: LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES
        }
    },
    {
        "confidence": "low",
        "conditions": ["CookingDomain"],
        "response": "[REDIRECT]"
    },
    {
        "confidence": "low",
        "conditions": ["DIYDomain"],
        "response": "[REDIRECT]"
    },
    {
        "confidence": "low",
        "conditions": ["MedicalDomain"],
        "response": {
            0: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            1: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            2: LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES
        }
    },
    {
        "confidence": "low",
        "conditions": ["FinancialDomain"],
        "response": {
            0: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            1: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            2: LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES
        }
    },
    {
        "confidence": "low",
        "conditions": ["LegalDomain"],
        "response": {
            0: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            1: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            2: LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES
        }
    },
    {
        "confidence": "low",
        "conditions": ["UndefinedDomain"],
        "response": {
            0: INTRO_PROMPTS,
            1: LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES,
            2: LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES
        }
    }

]
