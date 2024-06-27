# License MIT. by balestek https://github.com/balestek
from itertools import permutations


class Permute:
    def __init__(self, elements: dict):
        self.separators = ["", "_", "-", "."]
        self.elements = elements

    def gather(self, method: str = "strict" or "all") -> dict:
        permutations_dict = {}
        for i in range(1, len(self.elements) + 1):
            for subset in permutations(self.elements, i):
                if i == 1:
                    if method == "all":
                        permutations_dict[subset[0]] = self.elements[subset[0]]
                        permutations_dict["_" + subset[0]] = self.elements[subset[0]]
                        permutations_dict[subset[0] + "_"] = self.elements[subset[0]]
                else:
                    for separator in self.separators:
                        perm = separator.join(subset)
                        permutations_dict[perm] = self.elements[subset[0]]
                        if separator == "":
                            permutations_dict["_" + perm] = self.elements[subset[0]]
                            permutations_dict[perm + "_"] = self.elements[subset[0]]
        return permutations_dict
