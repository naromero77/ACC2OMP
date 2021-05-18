#!/usr/bin/python
# Author: Nichols A. Romero
# e-mail: naromer@anl.gov
# Argonne National Laboratory

# Python imports
import fileinput
import re
from shutil import copyfile

# Most common user configurable parameters
# Set to True for debugging and development purposes
debug = True
# Set to True to retain OpenACC directives in output
keepOpenACC = True

# Lists, dicts, and strings to aid in translation of OpenACC to OpenMP
# Note that the other way would be more difficult since OpenMP tends to
# be more verbose than OpenACC.

# In the variable names in the program, Dir stands for directive
# not directory.

ompDir = '!$omp'
accDir = '!$acc'
ompDirContinue = '!$omp&'
accDirContinue = '!$acc&'
nextLineContinue = '&'

emptyString = ''
singleSpaceString = ' '
transitionArrow = ' -> '
backupExtString = '.bak'

# directives without arguements
singleDirDict = {
    'loop': 'parallel do',
    'gang': emptyString,
    'independent': emptyString,
    'parallel': 'target teams distribute',
    'vector': 'simd',
    'routine': 'declare target',
    'seq': emptyString,
    'data': 'data',
    'end': 'end',
    'enter': 'target enter',
    'exit': 'target exit',
    'atomic': 'atomic',
    'serial': 'target',
    'declare': 'declare target',
}

dualDirDict = {}

# directives with arguements
singleDirwargsDict = {
    'attach': 'map(to:',
    'detach': 'map(from:',
    'copy': 'map(tofrom:',
    'copyin': 'map(to:',
    'copyout': 'map(from:',
    'create': 'map(alloc:',
    'delete': 'map(release:',
    'async': 'depend(out:',
    'wait': 'task depend(in:',
    'collapse': 'collapse(',
    'private': 'private(',
    'vector_length': 'simd simdlen(',
    'num_gangs': 'num_teams(',
    'present': emptyString,
}

dualDirwargsDict = {
    'update host': 'target update from(',
    'update device': 'target update to(',
}


def remove_extra_spaces(origString):
    """
    Converter needs extra spaces before and after commas and parenthesis
    removed in order work properly.
    """
    # Space before and after a comma
    newString = re.sub(' *, *', ',', origString)

    # Space before and after left parenthesis
    newString = re.sub(' *\( *', '(', newString)

    # Space before and after right parenthesis
    newString = re.sub(' *\) *', ')', newString)

    # Add space back in for continuation symbol
    newString = re.sub('\)&', ') &', newString)

    # Add space back when newString is adjacent to another variable or
    # directive
    # \w means any single letter, digit or underscore
    newString = re.sub('(\))(\w)', r'\1 \2', newString)

    return newString


def add_space_after_commas(origString):
    """
    Directives with arguements need spaces insert after commas.
    """
    # space after a comma
    newString = re.sub(',', ', ', origString)

    return newString


if __name__ == "__main__":
    # This list will contain the output buffer in a line-by-line breakup
    entries = []

    # Translate source file one line at a time
    lines = fileinput.input()

    for line in lines:
        # Remove extraneous spaces, but we only use
        # parsedLine for lines that actually contain directives
        origLine = line
        parsedLine = remove_extra_spaces(line)
        line = parsedLine

        if debug:
            print "extra spaces extracted below:"
            print line

        # Four cases to consider when parsing a line:
        # 1. Carriage return only
        # 2. White space only
        # 3. No OpenACC directive
        # 4. Line containing an OpenACC directive

        # First case is a line with only a CR
        if len(line) == 0:
            if debug:
                print 'Carriage return only'
            entries.append(origLine)
            continue

        # As long as the line is not empty (case #1), it can be
        # parsed. We need an iterable object and enumerate object
        # to aid in search for directives. We keep track of the
        # length of the line as well as its left justification,
        # but only use this when we are actually translating
        # directives (case #4)
        lenLine = len(line)
        numLeftSpaces = lenLine - len(line.lstrip(singleSpaceString))
        dirs = line.split()
        lenDirs = len(dirs)
        enumDirs = enumerate(dirs)

        # Second case is a line with only a whitespace
        if lenDirs == 0:
            if debug:
                print 'Blank line'
            entries.append(origLine)
            continue

        # Third case is a line that contains no directive
        # Use Booleans to keep track of when an OpenACC directive
        # has been found, by default we assume there is no
        # ACC directive present. Also allow for the possibility
        # that uppercase is used for the OpenACC directive, though
        # most people will use lowercase.
        accDirFound = False
        accDirContinueFound = False
        if ((dirs[0].lower() != accDir) and
                (dirs[0].lower() != accDirContinue)):
            if debug:
                    print 'No OpenACC directive on this line'
            entries.append(origLine)
            continue

        # Fourth case contains some OpenACC directive
        # From this point forward, we assume that a directive has
        # been found and we try to do a translation.
        # We will either find an OpenACC directive or a continuation
        # of an OpenACC directive. Check for both, but only one
        # must be found.
        if dirs[0].lower() == accDir: accDirFound = True
        if dirs[0].lower() == accDirContinue: accDirContinueFound = True

        # Detect whether they are using upper or lower case for the OpenACC
        # directive. Depending on the capitalization of the first instance
        # of an OpenACC pragma on that line will determine the
        # capitalization of the rest of the line. Mixed capitalization will
        # throw off this detection.
        accDirUpperCase = dirs[0].isupper()
        accDirLowerCase = dirs[0].islower()

        if debug:
            print "accDirUpperCase = ", accDirUpperCase
            print "accDirLowerCase = ", accDirLowerCase

        # Booleans cannot be both True or both False
        assert (accDirFound != accDirContinueFound)
        assert (accDirUpperCase != accDirLowerCase)

        if debug:
            print 'OpenACC directive present. Translating.'
            print dirs

        # These are the cases we consider
        # 1. Directive pairs. These are pairs of directives that only have
        #    meaning in combinations. Thus, they must be translated in pairs.
        # 2. Directive pairs with arguements.
        # 3. Directive single with no arguements.
        # 4. Directive single with scalar arguments.
        # 5. Directive single with multi-dimensional array arguements.

        # First find directive pairs, this is kludgy way to search through
        # directives but we do pairs first because there is overlap between
        # keywords among the different directive categories.

        # Counters which are only reset at each iteration of outer loop
        # NOTE: If present, totalDirsFound will count nextLineContinue symbol
        dualDir = None
        totalDirsFound = 0

        # Booleans to keep track of what directive type has been found
        # Need to be reset at each iteration of inner loop
        singleDirFound = False
        singleDirwargsFound = False
        dualDirFound = False
        dualDirwargsFound = False
        dirwargsFound = False
        for i, dir in enumDirs:
            # first iteration just put the OMP directive or continuation
            # version of it into a string and go to the next iteration
            if i == 0:
                newLine = singleSpaceString * numLeftSpaces
                if accDirUpperCase:
                    ompDir = ompDir.upper()
                    ompDirContinue = ompDirContinue.upper()
                else:  # accDirLowerCase is True
                    ompDir = ompDir.lower()
                    ompDirContinue = ompDirContinue.lower()
                if accDirFound:
                    newLine = newLine + ompDir
                else:  # accDirContinueFound is True
                    newLine = newLine + ompDirContinue
                continue

            # second iteration store the first pragma in the pair
            if i == 1:
                prevdir = dir

            # Special detection needed for line continuation
            if dir == nextLineContinue:
                totalDirsFound = totalDirsFound + 1
                newLine = newLine + singleSpaceString + nextLineContinue

            # Additional logic would be necessary if examining
            # triplets of directives
            # take adjacent directives and create new key
            # store previous two directives for next iteration
            # if i > 1:
            #     dualDir = prevdir + singleSpaceString + currentDir
            #     prevdrevdir = prevdir
            #    prevdir = dir

            # Some directives will have arguements, so we need to identify
            # those. The maxsplit arguement to the split method in dirwards
            # is needed to identify arrays properly. We split *only* on the
            # first parenthesis from the left hand side.
            #
            # Note that currentDir and dualDir must be in lowercase for pattern
            # matching purposes.
            dirwargs = dir.split('(', 1)
            lenDirwargs = len(dirwargs)
            currentDir = dirwargs[0].lower()
            dualDir = prevdir.lower() + singleSpaceString + currentDir

            if lenDirwargs > 1: dirwargsFound = True  # Boolean unused for now
            if debug:
                print 'dirwargs = ', dirwargs
                print 'dirwargs[0] = currentDir = ', currentDir
                print 'lenDirswargs = ', lenDirwargs
                print 'dualDir =', dualDir

            # identify which case we are in, only one can be true at any time
            # Need the check on dualDir equal None, because it will not exist
            # on iteration = 1.
            if dualDir is not None:
                if dualDir in dualDirDict:
                    print 'OpenACC Directive Dual with no argument found'
                    dualDirFound = True
                if dualDir in dualDirwargsDict:
                    print 'OpenACC Directive Dual with argument found'
                    dualDirwargsFound = True

            if currentDir in singleDirDict:
                print 'OpenACC Directive Single with no argument found'
                singleDirFound = True
            if currentDir in singleDirwargsDict:
                print 'OpenACC Directive Single with argument found'
                singleDirwargsFound = True

            # Tests that only one is true with XOR, if not, skip this iteration
            # and look for a pair, otherwise, Continue
            if not (singleDirFound ^ singleDirwargsFound ^
                    dualDirFound ^ dualDirwargsFound):
                if debug:
                    print "Next Iteration will check for Dual Directives Found"
                continue
            else:
                assert(singleDirFound ^ singleDirwargsFound ^
                       dualDirFound ^ dualDirwargsFound)

            # Code below generates the new directives depending on the value
            # of the boolean, probably need a function instead.

            # (single) directive with no arguements
            if singleDirFound:
                totalDirsFound = totalDirsFound + 1
                if debug:
                    print 'OpenACC Directive Single with no argument found'
                newDir = singleDirDict[currentDir]
                if newDir == emptyString: continue
                if accDirUpperCase: newDir = newDir.upper()
                if debug: print currentDir + transitionArrow + newDir
                newLine = newLine + singleSpaceString + newDir

            # (single) directive with an arguement
            if (lenDirwargs > 1) and singleDirwargsFound:
                totalDirsFound = totalDirsFound + 1
                if debug: print 'OpenACC Directive Single with argument found'
                newDir = singleDirwargsDict[currentDir]
                if newDir == emptyString: continue
                if accDirUpperCase: newDir = newDir.upper()
                newLine = newLine + singleSpaceString + newDir
                # for-loop handles the arguement component
                for j in range(1, lenDirwargs):
                    newDir = dirwargs[j]
                    if debug: print currentDir + transitionArrow + newDir
                    newLine = newLine + newDir

            # (pair) directive with no arguement
            if dualDirFound:
                totalDirsFound = totalDirsFound + 2
                if debug:
                    print 'OpenACC Directive Dual with no arguement found'
                newDir = dualDirDict[dualDir]
                if newDir == emptyString: continue
                if accDirUpperCase: newDir = newDir.upper()
                if debug:
                    print dualDir + transitionArrow + newDir
                newLine = newLine + singleSpaceString + newDir

            # (pair) directive with an arguement
            if (lenDirwargs > 1) and dualDirwargsFound:
                totalDirsFound = totalDirsFound + 2
                if debug: print 'OpenACC Directive Dual with an argument'
                newDir = dualDirwargsDict[dualDir]
                if newDir == emptyString: continue
                if accDirUpperCase: newDir = newDir.upper()
                newLine = newLine + singleSpaceString + newDir
                # for-loop handles the arguement component
                for j in range(1, lenDirwargs):
                    newDir = dirwargs[j]
                    if debug: print dualDir + transitionArrow + newDir
                    newLine = newLine + newDir

            # reset booleans for next iteration
            singleDirFound = False
            singleDirwargsFound = False
            dualDirFound = False
            dualDirwargsFound = False
            dirwargsFound = False

            # End of inner loop on `i`

        # On last Loop iteration, check that you were able to translate
        # all directives. The minus one in the first conditional takes into
        # account the initial `!$acc` or `!$acc&` which is not counted.
        # If the directive cannot be translated, keep line AS IS and
        # output original line containing OpenACC.
        if (totalDirsFound < (lenDirs - 1)):
            if debug:
                print 'lenDirs=', lenDirs
                print 'totalDirsFound=', totalDirsFound
                print 'OpenACC directive could not be translated.'
            newLine = origLine
        else:
            if keepOpenACC:  # append original line into the buffer
                entries.append(origLine)
            newLine = add_space_after_commas(newLine) + '\n'

        # Finally we add the new line into the buffer
        entries.append(newLine)

        # End of outer loop on `line`

    # We intentionally wait until the entire file is read because
    # fileinput module will return None only after the entire file
    # has been read.
    # First we backup the file, we have to resort to using the sys
    # module to get the filename because the filename() method
    # returns None unless the entire file has been read.
    currentFilename = lines.filename()
    backupFilename = currentFilename + backupExtString
    copyfile(currentFilename, backupFilename)

    if debug:
        print 'Current Filename: ', currentFilename
        print 'Backup Filename: ', backupFilename

    # Close the current open file
    lines.close()

    # Open a new file to write to that has the same source filename.
    # Looks like the file is modified in-place, but this is not the
    # case. Write the translated file to disk with the original filename
    with open(currentFilename, 'w') as theFile:
        theFile.write(''.join(entries))
