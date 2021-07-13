def isValidTCID(value):
    value = str(value)

    if not len(value) == 11:
        return False

    if not value.isdigit():
        return False

    if int(value[0]) == 0:
        return False

    digits = [int(d) for d in str(value)]

    if not sum(digits[:10]) % 10 == digits[10]:
        return False

    if not (((7 * sum(digits[:9][-1::-2])) - sum(digits[:9][-2::-2])) % 10) == digits[9]:
        return False

    return True


def taxnum_checker(t):
    t = str(t)

    if not (len(t) == 10) | (len(t) == 11):
        return False

    if not t.isdigit():
        return False

    if len(t) == 10:
        total = 0
        for x in range(0, 9):
            tmp1 = (int(t[x]) + (9 - x)) % 10
            tmp2 = (tmp1 * (2 ** (9 - x))) % 9
            if tmp1 != 0 and tmp2 == 0:
                tmp2 = 9

            total += tmp2

        if total % 10 == 0:
            check_num = 0
        else:
            check_num = 10 - (total % 10)

        return int(t[9]) == check_num

    if len(t) == 11:
        return isValidTCID(t)