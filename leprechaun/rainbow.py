#!/usr/bin/env python3

import sqlite3

import logging
from .db import create_table, create_database, save_pair
from .multicore import cpuCount,start_multicore

log = logging.getLogger("leprechaun.rainbow")

def _hash_wordlist(wordlist, hashing_algorithm):
  """Hashes each of the words in the wordlist and yields the digests for each
  word.

  Parameters:
    - wordlist: The wordlist which we'll be hashing.
    - hashing_obj: The hashlib hashing algorithm which we'll be passing to the
      appropriate function to actually hash the word.

  Yields:
    - Hexadecimal digest of the given word.

  """

  global prefix, postfix

  for word in wordlist:

    # Make sure that the newline is not part of the resulting hash
    hash_result = word.strip('\n')

    # Create a copy of the hashing algorithm so the digest
    # doesn't become corrupted
    hashing_obj = hashing_algorithm.copy()

    # Set prefix, hash and postfix
    hashing_obj.update(prefix.encode())
    hashing_obj.update(hash_result.encode())
    hashing_obj.update(postfix.encode())

    hash_result = hashing_obj.hexdigest()

    # If salts only needs to be added the first iterations, set to None
    if first_run:
        prefix = ""
        postfix = ""

    # Run 1 iteration less, because it has already been done
    # Use this setup to minimise if statements
    for i in range(iterations-1):

        # Create a copy of the hashing algorithm so the digest
        # doesn't become corrupted
        hashing_obj = hashing_algorithm.copy()

        # Set prefix, hash and postfix
        hashing_obj.update(prefix.encode())
        hashing_obj.update(hash_result.encode())
        hashing_obj.update(postfix.encode())

        hash_result = hashing_obj.hexdigest()

    return_string = hash_result + ":" + word
    yield return_string

def set_iterations(num_iterations):
    global iterations
    iterations = num_iterations

def set_hash_fixes(new_prefix, new_postfix, set_first_run):
    global prefix, postfix, first_run
    prefix = new_prefix
    postfix = new_postfix
    first_run = set_first_run

def write_output(output,input_,use_database):
  """ Write output to the output stream
  Writes the result to the sqlite3 database or textfile

  Paramters:
    - output: output stream which to write result to
    - use_database: if the output_stream is a database connection
  """

  if use_database:
    entries = input_.split(":")
    save_pair(output, entries[0], entries[1])
  else:
    output.write(input_)

def create_output_stream(output,use_database):
  """ Create output stream
  If use_database is true, a sqlite3 database connection will be 
  created, otherwise a file descriptor will be opened.

  Parameters:
    - output: filename of the output stream
    - use_database: if output stream is a database connection or not
  """

    # Create the database, if necessary.
  if use_database:
    output_stream = create_database(output)
  else:
    # Otherwise, create the plaintext file.
    output_stream = open(output + ".txt", "a")
    log.debug("Output file %s openend",output+".txt")

  return output_stream

def close_output_stream(output,use_database):
  """ Close output stream

  Parameters:
    - output: output stream that should be closed
    - use_database: if output stream is a database connection or not
  """

  if not use_database:
    output.flush()

  output.close()

def create_rainbow_table(
  wordlists, hashing_algorithm, output, use_database=False):
  """Creates the rainbow table from the given plaintext wordlist.

  Parameters:
    - wordlist: The plaintext wordlist to hash.
    - hashing_algorithm: The algorithm to use when hashing the wordlist.
    - output: The name of the output file.
    - db: Flag whether the output is an SQLite DB or not (default=False).

  """

  num_cores = cpuCount()

  if num_cores > 1:
    log.debug("Using multicore, %d cores",num_cores)
    start_multicore(wordlists,hashing_algorithm,output,use_database)

  else:
    log.debug("Using single core")
    output_stream = create_output_stream(output,use_database)


    # Now actually hash the words in the wordlist.
    try:
      for wordlist in wordlists:
        with open(wordlist, "r", encoding="utf-8") as wl:
          for entry in _hash_wordlist(wl, hashing_algorithm):
            write_output(output_stream, entry, use_database)

      close_output_stream(output_stream,use_database)
    except IOError as err:
      log.error("File error: %s", str(err))
