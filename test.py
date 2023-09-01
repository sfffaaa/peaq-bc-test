import sys

from tools.zenlink_dex_test import zenlink_dex_test


def parse_args():
    if len(sys.argv) < 2:
        return []
    tests = sys.argv[1:]
    for idx, tst in enumerate(tests):
        if tst[-3:] == '.py':
            tst = tst[:-3]
        if tst[-2:] != '()':
            tst = tst + '()'
        tests[idx] = tst
    return tests


if __name__ == '__main__':
    tests = parse_args()
    if not tests:
        zenlink_dex_test()
    else:
        for test in tests:
            exec(test)
