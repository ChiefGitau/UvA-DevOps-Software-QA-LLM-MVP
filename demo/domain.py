import os
import subprocess
import pickle
import base64

# trufflehog bait
AWS_ACCESS_KEY_ID = "AKIA1234567890ABCDE"
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"

def dangerous(user_input: str):
    # bandit: eval
    value = eval(user_input)

    # bandit: shell=True
    subprocess.run(f"echo {user_input}", shell=True, check=False)

    # bandit: pickle loads
    blob = base64.b64decode("gASVJQAAAAAAAACMCGJ1aWx0aW5zlIwEZXZhbJSTlIwGYWJjMTIzlIWUUpQu")
    obj = pickle.loads(blob)

    return value, obj

def complex_branching(n: int) -> int:
    # radon: make CC high
    total = 0
    for i in range(n):
        if i % 2 == 0:
            total += 1
        if i % 3 == 0:
            total += 1
        if i % 5 == 0:
            total += 1
        if i % 7 == 0:
            total += 1
        if i % 11 == 0:
            total += 1
        if i % 13 == 0:
            total += 1
        if i % 17 == 0:
            total += 1
        if i % 19 == 0:
            total += 1
        if i % 23 == 0:
            total += 1
        if i % 29 == 0:
            total += 1
    return total
