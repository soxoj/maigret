import sys
import difflib
import requests


a = requests.get(sys.argv[1]).text
b = requests.get(sys.argv[2]).text


tokens_a = set(a.split('"'))
tokens_b = set(b.split('"'))

a_minus_b = tokens_a.difference(tokens_b)
b_minus_a = tokens_b.difference(tokens_a)

print(a_minus_b)
print(b_minus_a)

print(len(a_minus_b))
print(len(b_minus_a))

desired_strings = ["username", "not found", "пользователь", "profile", "lastname", "firstname", "biography",
"birthday", "репутация", "информация", "e-mail"]


def get_match_ratio(x):
    return round(max([
    	difflib.SequenceMatcher(a=x.lower(), b=y).ratio()
    	for y in desired_strings
    ]), 2)


RATIO = 0.6

print(sorted(a_minus_b, key=get_match_ratio, reverse=True)[:10])
print(sorted(b_minus_a, key=get_match_ratio, reverse=True)[:10])