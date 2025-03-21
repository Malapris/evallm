GOAL:
Merge the following JSON objects into a single JSON by merging each values separated by '|' and avoid duplicate values.
For similar values, try to find a synthesis between them, otherwise concatenate the values with '|' as a separator.
You must absolutely respect the OUTPUT JSON FORMAT .
ALL JSON OBJECTS ARE VALID AND REPRESENT THE VERY SAME CONTEST.
IMPORTANT : Return only the merged JSON, without introductions, comments or explanations.
Return only one JSON, nothing else. Do not return a list, return only one JSON.

OUTPUT JSON FORMAT you must respect absolutely (key:meaning) :
[ {
    "Titre": "the contest title. You must get the best match for the Title regarding all options.",
    "Type": "the type of contest (example: photo, drawing, painting, etc.).",
    "Organisateur": "the name of the contest organizer with their nationality and location.",
    "Description": "generate a synthetic summary in French from the original description, without considering tone, with only interesting information that you can list (separated by '|').",
    "Description_originale": "complete and original description of the contest without translation or summary.",
    "Images": "complete URLs of images associated with the contest, separated by '|'. Only take those related to the contest!",
    "Theme": "The theme of the contest (example: portrait, human, nature, animals, artistic, etc.), there can be multiple separated by '|'.",
    "Portee": "The scope of the contest with a score from 0 to 10 where 10 is maximum, meaning the interest in participating with the visibility/notoriety it can bring and the prizes it offers.",
    "Prix": "the prizes to be won with this contest (money, gifts, internship, etc.). If it's money you give the amount directly. If there are several, you make a list with separation by '|'.",
    "Eligibilite": "The terms and conditions for participating in the contest (particularly check nationality, age, location and gender).",
    "Date": "the deadline for contest participation in Year/Month/Day format (example: 2025/12/31). If you don't have the information, don't put the date.",
    "Selection": "how the selection process works: jury or vote or others.",
    "Frais": "participation or registration fees for the contest. If you have the amount put it with the currency, if you just know it's paid, put 'Paid'. If there are several amounts, separate them with '|'.",
    "URL": "links associated with the contest, they must be separated by '|', keep them intact."
} ]
