"""
Medication ↔ Local Cuisine Risk Engine
Detects dangerous interactions between user medications and local dishes at the destination.

This is clinically significant — e.g. Warfarin + Natto (Japan) = dangerous Vitamin K spike.
"""

from typing import List, Dict, Any
from app.services.destination_normalizer import normalize_destination

# Clinical medication-to-food interaction database
# Sources: FDA, NIH, clinical pharmacology references
MEDICATION_CUISINE_RISKS: Dict[str, Dict[str, Any]] = {
    "Warfarin": {
        "high_risk_foods": ["natto", "spinach", "kale", "seaweed", "wakame", "kombu", "nori",
                            "edamame", "green tea", "liver", "nato"],
        "high_risk_dishes": ["Natto", "Natto Don", "Natto Soba", "Hiyayakko", "Tofu Salad",
                             "Spinach Ohitashi", "Seaweed Salad", "Edamame", "Miso Soup with Seaweed",
                             "Saag Paneer", "Palak Paneer", "Green Tea Ice Cream"],
        "risky_cuisines": ["Japanese", "Korean", "Indian"],
        "warning": "Warfarin anticoagulation is highly sensitive to Vitamin K intake. Natto (fermented soybeans) in Japanese cuisine contains extremely high Vitamin K2 and can dramatically reduce Warfarin effectiveness, increasing clotting risk. Avoid Natto entirely. Maintain consistent intake of other Vitamin K foods.",
        "severity": "Critical",
        "avoid_keyword_signals": ["natto", "seaweed", "spinach", "kale", "edamame"]
    },
    "Atorvastatin": {
        "high_risk_foods": ["grapefruit", "grapefruit juice", "pomelo"],
        "high_risk_dishes": ["Grapefruit Juice", "Grapefruit Sorbet", "Pomelo Salad",
                             "Som Tum (with Pomelo)", "Yam Som-O"],
        "risky_cuisines": ["Thai", "Vietnamese"],
        "warning": "Grapefruit and pomelo contain furanocoumarins that inhibit CYP3A4, the enzyme that metabolizes Atorvastatin. This can lead to dangerously high statin blood levels, increasing the risk of muscle damage (rhabdomyolysis). Avoid all grapefruit and pomelo products.",
        "severity": "High",
        "avoid_keyword_signals": ["grapefruit", "pomelo"]
    },
    "Statins": {
        "high_risk_foods": ["grapefruit", "pomelo"],
        "high_risk_dishes": ["Grapefruit Juice", "Pomelo Salad", "Som Tum (with Pomelo)"],
        "risky_cuisines": ["Thai", "Vietnamese"],
        "warning": "Statins interact with grapefruit and pomelo. These fruits inhibit the enzyme that breaks down statins, causing dangerous drug accumulation. Avoid grapefruit and pomelo at all times.",
        "severity": "High",
        "avoid_keyword_signals": ["grapefruit", "pomelo"]
    },
    "Metformin": {
        "high_risk_foods": ["alcohol", "beer", "sake", "wine"],
        "high_risk_dishes": ["Sake", "Beer", "Shabu-Shabu with sake broth", "Tempura Beer"],
        "risky_cuisines": ["Japanese", "German"],
        "warning": "Alcohol combined with Metformin significantly increases the risk of lactic acidosis, a rare but life-threatening condition. Avoid all alcoholic beverages, including sake at Japanese restaurants.",
        "severity": "High",
        "avoid_keyword_signals": ["sake", "alcohol", "beer", "wine", "spirit"]
    },
    "Cyclosporine": {
        "high_risk_foods": ["grapefruit", "pomelo", "St. John's Wort"],
        "high_risk_dishes": ["Grapefruit Juice", "Pomelo Salad"],
        "risky_cuisines": ["Thai"],
        "warning": "Grapefruit severely increases Cyclosporine blood levels through CYP3A4 inhibition, increasing risk of toxicity. Avoid all grapefruit products.",
        "severity": "Critical",
        "avoid_keyword_signals": ["grapefruit", "pomelo"]
    },
    "Monoamine Oxidase Inhibitors": {
        "high_risk_foods": ["tyramine", "aged cheese", "soy sauce", "miso", "fermented foods",
                            "kimchi", "sauerkraut", "wine", "beer", "salami"],
        "high_risk_dishes": ["Kimchi", "Miso Soup", "Soy Glazed Chicken", "Teriyaki",
                             "Aged Cheese Plate", "Charcuterie", "Sauerkraut"],
        "risky_cuisines": ["Japanese", "Korean", "German", "French"],
        "warning": "MAO Inhibitors combined with tyramine-rich foods (fermented, aged, cured) can cause a dangerous hypertensive crisis. Japanese miso, soy sauce, Korean kimchi, and aged French cheeses all contain high tyramine levels.",
        "severity": "Critical",
        "avoid_keyword_signals": ["miso", "soy sauce", "kimchi", "fermented", "aged cheese"]
    }
}

def get_local_cuisine_drug_risks(
    medications: List[str],
    destination: str
) -> List[Dict[str, Any]]:
    """
    For each user medication, checks if the destination cuisine poses clinical risks.
    Returns structured warning objects for each dangerous interaction found.
    
    Args:
        medications: List of medication names from health profile
        destination: The user's travel destination (city or country)
    
    Returns:
        List of risk objects with medication, dish, warning, and severity
    """
    norm = normalize_destination(destination)
    dest_cuisine = norm.get("cuisine", "")
    dest_country = norm.get("country", "")
    
    risks = []
    for med in medications:
        # Case-insensitive lookup with partial matching for brand/generic names
        med_data = None
        for key, data in MEDICATION_CUISINE_RISKS.items():
            if key.lower() in med.lower() or med.lower() in key.lower():
                med_data = (key, data)
                break
        
        if not med_data:
            continue
            
        med_name, data = med_data
        risky_cuisines = data.get("risky_cuisines", [])
        
        # Check if the destination cuisine matches a risky cuisine for this drug
        cuisine_match = any(
            rc.lower() in dest_cuisine.lower() or dest_cuisine.lower() in rc.lower()
            for rc in risky_cuisines
        )
        
        if cuisine_match or data.get("high_risk_dishes"):
            risks.append({
                "medication": med_name,
                "destination": dest_country,
                "destination_cuisine": dest_cuisine,
                "severity": data.get("severity", "Moderate"),
                "warning": data.get("warning", ""),
                "specific_dishes_to_avoid": data.get("high_risk_dishes", []),
                "foods_to_avoid": data.get("high_risk_foods", []),
                "cuisine_is_high_risk": cuisine_match
            })
    
    return risks


def format_risk_warnings(risks: List[Dict[str, Any]]) -> List[str]:
    """Formats risk objects into human-readable warning strings for the MissionResult."""
    warnings = []
    for risk in risks:
        severity = risk.get("severity", "")
        med = risk.get("medication", "")
        cuisine = risk.get("destination_cuisine", "")
        dishes = risk.get("specific_dishes_to_avoid", [])[:3]  # limit to 3
        warning_text = risk.get("warning", "")[:150]  # truncate for display
        
        dish_str = f" Avoid: {', '.join(dishes)}." if dishes else ""
        warnings.append(
            f"[{severity}] {med} + {cuisine} Cuisine: {warning_text}...{dish_str}"
        )
    return warnings
