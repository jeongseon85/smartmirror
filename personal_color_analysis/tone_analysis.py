# personal_color_analysis/tone_analysis.py

def is_warm(lab_b, a):
    warm_b_std = [11.6518, 11.71445, 3.6484]
    cool_b_std = [4.64255, 4.86635, 0.18735]

    warm_dist = 0
    cool_dist = 0

    for i in range(len(lab_b)):
        warm_dist += abs(lab_b[i] - warm_b_std[i]) * a[i]
        cool_dist += abs(lab_b[i] - cool_b_std[i]) * a[i]

    return warm_dist <= cool_dist

def is_spr(hsv_s, a):
    spr_s_std = [18.59296, 30.30303, 25.80645]
    fal_s_std = [27.13987, 39.75155, 37.5]

    spr_dist = 0
    fal_dist = 0

    for i in range(len(hsv_s)):
        spr_dist += abs(hsv_s[i] - spr_s_std[i]) * a[i]
        fal_dist += abs(hsv_s[i] - fal_s_std[i]) * a[i]

    return spr_dist <= fal_dist

def is_smr(hsv_s, a):
    smr_s_std = [12.5, 21.7195, 24.77064]
    wnt_s_std = [16.73913, 24.8276, 31.3726]
    
    smr_dist = 0
    wnt_dist = 0
    
    for i in range(len(hsv_s)):
        smr_dist += abs(hsv_s[i] - smr_s_std[i]) * a[i]
        wnt_dist += abs(hsv_s[i] - wnt_s_std[i]) * a[i]
        
    return smr_dist <= wnt_dist