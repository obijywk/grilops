import argparse
import os
import re
import subprocess
import sys


def execute(example_path):
  completed_process = subprocess.run(
      ["python3", example_path],
      stdout=subprocess.PIPE,
      check=True
  )
  return completed_process.stdout


def print_diffs(diffs):
  for filename, actual, expected in diffs:
    print(f"=== {filename}")
    print("=== Output:")
    print(str(actual, "utf-8"))
    print("=== Expected:")
    print(str(expected, "utf-8"))
    print()


def main():
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument(
    "-f", "--filename_regexp",
    help="only check files with names that match this regexp",
    type=str
  )
  arg_parser.add_argument(
    "-u", "--update",
    help="rewrite any golden files that have changed",
    action="store_true"
  )
  args = arg_parser.parse_args()

  examples_path = os.path.join(os.path.dirname(__file__), "..", "examples")
  failed = False
  diffs = []
  for filename in os.listdir(examples_path):
    if not filename.endswith(".py"):
      continue
    if args.filename_regexp:
      if not re.match(args.filename_regexp, filename):
        continue
    sys.stdout.write(f"{filename:32}")
    sys.stdout.flush()

    golden_path = os.path.join(
        os.path.dirname(__file__), "golden", filename + ".txt")
    if os.path.isfile(golden_path):
      with open(golden_path, "rb") as golden_file:
        golden_data = golden_file.read()
    else:
      if not args.update:
        failed = True
        print("\x1b[1;33mMISSING\x1b[0m")
        continue
      golden_data = None

    example_path = os.path.join(examples_path, filename)
    try:
      test_data = execute(example_path)
      if test_data == golden_data:
        print("\x1b[1;32mPASS\x1b[0m")
      else:
        if args.update:
          with open(golden_path, "wb") as golden_file:
            golden_file.write(test_data)
          print("\x1b[1;33mUPDATED\x1b[0m")
        else:
          failed = True
          print("\x1b[1;31mFAIL\x1b[0m")
          diffs.append((filename, test_data, golden_data))
    except subprocess.CalledProcessError:
      failed = True
      print("\x1b[1;31mERROR\x1b[0m")

  if failed:
    print_diffs(diffs)
    sys.exit(1)


if __name__ == "__main__":
  main()
