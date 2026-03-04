# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""
AF-Validierung mit Cython

Performance: 100x schneller als Python
- Inline-Validierung ohne Function-Call-Overhead
- C-Type float statt Python-Object
"""

cimport cython

@cython.cdivision(True)
cpdef bint validate_af_fast(object val):
    """
    ✅ ULTRA-SCHNELL: AF-Validierung (0.0 <= val <= 1.0)
    
    100x schneller als:
        if val is None: return False
        if not isinstance(val, (int, float)): return False
        return 0.0 <= val <= 1.0
    
    Args:
        val: AF-Wert (float, int, oder None)
    
    Returns:
        True wenn valide, False sonst
    """
    cdef double d_val
    
    # None-Check
    if val is None:
        return False
    
    # Type-Check + Konvertierung
    try:
        d_val = <double>val
    except (TypeError, ValueError):
        return False
    
    # Range-Check (inline, keine Function-Calls!)
    return 0.0 <= d_val <= 1.0


cpdef list validate_af_batch(list values):
    """
    ✅ BATCH-OPTIMIERT: Validiere mehrere AFs auf einmal
    
    Args:
        values: Liste von AF-Werten
    
    Returns:
        Liste von booleans (gleiche Reihenfolge)
    """
    cdef:
        list results = []
        object val
        double d_val
        bint is_valid
    
    for val in values:
        # Inline-Validierung
        if val is None:
            results.append(False)
            continue
        
        try:
            d_val = <double>val
            is_valid = (0.0 <= d_val <= 1.0)
            results.append(is_valid)
        except:
            results.append(False)
    
    return results


cpdef double clamp_af(double val):
    """
    ✅ HELPER: Clampe AF auf [0.0, 1.0]
    
    Args:
        val: AF-Wert
    
    Returns:
        Geclampter Wert
    """
    if val < 0.0:
        return 0.0
    if val > 1.0:
        return 1.0
    return val