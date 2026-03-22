from datetime import datetime

def derive_student_data(email: str) -> dict:
    if not email or "@" not in email:
        return {}
        
    prefix = email.split('@')[0].upper()
    # Expecting format like 2022UCH1062 (11 chars) or 2023UCP1573
    if len(prefix) < 7:
        return {}
        
    year_str = prefix[:4]
    dept_code = prefix[4:7]
    
    DEPARTMENT_MAP = {
        "UCP": "Computer Science and Engineering",
        "UEC": "Electronics and Communication Engineering",
        "UEE": "Electrical Engineering",
        "UME": "Mechanical Engineering",
        "UCH": "Chemical Engineering",
        "UCE": "Civil Engineering",
        "UMT": "Metallurgical and Materials Engineering",
        "UAI": "Artificial Intelligence and Data Engineering",
        "UAR": "Architecture and Planning"
    }
    
    derived = {}
    
    # 1. Department
    if dept_code in DEPARTMENT_MAP:
        derived["department"] = DEPARTMENT_MAP[dept_code]
    
    # 2. Year
    try:
        start_year = int(year_str)
        now = datetime.now()
        # Year logic: boundary is July 21st
        calc_year = now.year - start_year
        if now.month > 7 or (now.month == 7 and now.day >= 21):
            calc_year += 1
        elif now.month < 7 or (now.month == 7 and now.day < 21):
            # If we are before July 21, the academic year didn't increment yet
            pass
        
        if 1 <= calc_year <= 6: # Standard degree lengths
            derived["year"] = calc_year
    except ValueError:
        pass
        
    return derived
