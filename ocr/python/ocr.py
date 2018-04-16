#!/usr/bin/env python
import sys, re

checksum_on = False
digits = {
  (
    '   ',
    '  |',
    '  |'
  ): '1',
  (
    ' _ ',
    ' _|',
    '|_ '
  ): '2',
  (
    ' _ ',
    ' _|',
    ' _|'
  ): '3',
  (
    '   ',
    '|_|',
    '  |'
  ): '4',
  (
    ' _ ',
    '|_ ',
    ' _|'
  ): '5',
  (
    ' _ ',
    '|_ ',
    '|_|'
  ): '6',
  (
    ' _ ',
    '  |',
    '  |'
  ): '7',
  (
    ' _ ',
    '|_|',
    '|_|'
  ): '8',
  (
    ' _ ',
    '|_|',
    ' _|'
  ): '9',
  (
    ' _ ',
    '| |',
    '|_|'
  ): '0',
}

def dbg(x):
  print(x)
  return x

# print('digits = {')
# print('}\n')
def dict_print(position, slug): # used to generate digits, above
  print('  (\n' + ', \n'.join(f"    '{s}'" for s in slug) + '\n  ): ' + str(position + 1) + ',')

def slout(slug):
  return '\n'.join(slug)

def slugs(account_lines):
  return [
    tuple(line[position*3 : position*3 + 3] for line in account_lines)
       for position in range(9)
  ]

def checksum_total(account):
  return sum(x * int(account[-x]) for x in range(1, 10))

def checksum(account):
  return checksum_total(account) % 11

def illegible(account):
  return re.search(r'\?', account)

def bad_checksum(account):
  return checksum_on and checksum(account) != 0

def is_ambiguous(account):
  return illegible(account) or bad_checksum(account)

def account_string(account):
  if illegible(account):
    return account + ' ILL'
  elif bad_checksum(account):
    return account + ' ERR'
  else: 
    return account

def slugs_to_digits(slugs):
  return ''.join( digits.get(slug, '?') for slug in slugs )

def account_output(lines):
  original_slugs = slugs(lines)
  account = slugs_to_digits(original_slugs)
  str = account_string(account)
  if len(str) != 9: 
    alternates = []
    for index, slug in enumerate(original_slugs):
      for alternate_slug in alternate_slugs(slug, digits.get(slug)):
        rewritten_slugs = list(original_slugs)
        rewritten_slugs[index] = alternate_slug
        alternate_account = slugs_to_digits(rewritten_slugs)
        alternate_string = account_string(alternate_account)
        if len(alternate_string) == 9:
          alternates.append(alternate_account)
    if len(alternates) == 1:
      return alternates[0]
    elif len(alternates) == 0:
      return str
    else:
      return f'{account} AMB {sorted(alternates)!r}'
        
  return str

def alternate_slugs(slug, digit):
  result = set()
  swaps = ['_', '|', ' ']
  for row in range(3):
    for col in range(3):
      for swap in swaps:
        corrupted_slug = [list(strip) for strip in slug]
        corrupted_slug[row][col] = swap
        corrupted_slug = tuple(''.join(chars) for chars in corrupted_slug)
        if corrupted_slug == slug: continue
        new_digit = digits.get(corrupted_slug)
        if (new_digit == digit): continue
        result.add(corrupted_slug)
  return result


def process_test(account_string, expected):
  if expected == ''.join(account_string):
    print(f'generated expected: {account_string}')
  else:
    print('ERROR: generated mismatch:')
    print(f'expected: "{expected}"')
    print(f'actual  : "{account_string}"')

def process_accounts_file():
  print('process accounts')
  with open('../testcases.txt') as lines:
    account_lines = []
    for line in lines:
      line = line[:-1]
      if line.startswith('TESTS '):
        print('tests')
        if re.search('use case 3', line):
          global checksum_on
          checksum_on = True
      elif line.startswith('BREAK'):
        #sys.exit(0)
        raise Exception 
      else:
        line = line[4:]
        if line.startswith('=>'):
          process_test(account_string, line[3:])
        elif len(account_lines) < 3:
          account_lines.append(line)
        else:
          account_string = account_output(account_lines)
          account_lines = []
    
process_accounts_file()

