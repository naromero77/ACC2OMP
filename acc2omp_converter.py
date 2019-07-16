#!/usr/bin/python
# Author: Nichols A. Romero
# e-mail: naromer@anl.gov
# Argonne National Laboratory

# Known limitations:
# - OpenACC -> OpenMP directive mapping must be explicitly available in a dictionary
# - OpenACC async is not handled properly because of fundamental differences between OpenACC and OpenMP
# - Only handles Fortran
# - Search string tokens are case dependent
# - Hard coded to a specific file name at the moment


# Lists, dicts, and strings to aid in translation of OpenACC to OpenMP
# Note that the other way would be more difficult since OpenMP tends to
# be more verbose than OpenACC.

# In the variable names in the program, Dir stands for directive
# not directory.

import sys
import fileinput
from shutil import copyfile

ompDir = '!$omp'
accDir = '!$acc'
ompDirContinue = '!$omp&'
accDirContinue = '!$acc&'

singleSpaceString = ' ' 
doubleSpaceString = '  '
transitionArrow = ' -> '
backupExtString = '.bak'

# no arguements
singleDirDict = {
    'loop' : 'parallel do',
    'gang' : '', 
    'parallel' : 'target teams distribute',
    'vector' : 'simd', 
    'routine' : 'declate target',
    'seq' : '',
    'data' : 'data',
    'enter' : 'target enter',
    'exit' : 'target exit',
}

dualDirDict = {
    'atomic update' : 'atomic update',
}

# with arguements
singleDirwargsDict = {
    'copy' : 'map(tofrom:',   
    'copyin' : 'map(to:',
    'copyout' : 'map(from:' ,
    'create' : 'map(alloc:' ,
    'delete' : 'map(release:' ,
    'async' : 'depend(out:',
    'wait' : 'task depend(in:' ,
    'collapse' : 'collapse(',
    'private' : 'private(',
    'vector_length' : 'simd simdlen(',
    'num_gangs' : 'num_teams('
}
    
dualDirwargsDict = {
    'update device' : 'target update(',
}

# Set to 1 for debugging and development purposes
debug = 1

if __name__ == "__main__" :
    # This list will contain the output buffer in a line-by-line breakup
    entries = []

    # Translate source file one line at a time
    lines = fileinput.input()


    
    for line in lines:
        if debug:
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
            entries.append(line)
            continue

        # As long as the line is not empty (case #1), it can be
        # parsed. We need an iterable object and enumerate object
        # to aid in search for directives
        dirs = line.split()
        lenDirs = len(dirs)
        enumDirs = enumerate(dirs)
        
        # Second case is a line with only a whitespace
        if lenDirs == 0:
            if debug:
                print 'Blank line'
            entries.append(line)
            continue

        # Third case is a line that contains no directive
        # Use Booleans to keep track of OpenACC directives founds
        # we assume they have NOT been found
        accDirFound = False
        accDirContinueFound = False        
        if ((dirs[0] != accDir) and (dirs[0] != accDirContinue)):
            if debug:
                    print 'No OpenACC directive on this line'
            entries.append(line)
            continue

        # Fourth case contains some OpenACC directive
        # From this point forward, we assume that a directive has
        # been found and we try to do a translation.
        # We will either find an OpenACC directive or a continuation
        # of an OpenACC directive. Check for both, but only one
        # must be found.
        if dirs[0] == accDir: accDirFound = True
        if dirs[0] == accDirContinue: accDirContinueFound = True

        # Booleans cannot be both True or both False
        assert (accDirFound != accDirContinueFound)
         
        if debug:
            print 'OpenACC directive present. Translating.'
            print dirs

        # These are the cases we consider
        # 1. Directive pairs. These are pairs of directives that only have
        #    meaning in combinations. Thus, they must be translated in pairs.
        # 2. Directive pairs with arguements
        # 3. Directive single with no arguements. 
        # 4. Directive single with scalar arguments.
        # 5. Directive single with multi-dimensional array arguements.

        # First find directive pairs, this is kludgy way to search through
        # directives but we do pairs first because there is overlap between
        # keywords among the different directive categories.

        # Booleans to keep track of what directive type has been found:
        dualDir = None
        singleDirFound = False
        singleDirwargsFound = False
        dualDirFound = False
        dualDirwargsFound = False
        dirwargsFound = False
        for i, dir in enumDirs:
            # first iteration just put the OMP directive or continuation version
            # of it into a string and go to the next iteration
            if i == 0:
                if accDirFound: newLine = doubleSpaceString + ompDir
                if accDirContinueFound: newLine = doubleSpaceString + ompDirContinue
                continue

            # second iteration store the first pragma in the pair
            if i == 1:
                prevdir = dir

            # take adjacent directives and create new key
            # store previous two directives for next iteration
            # if i > 1:
            #     dualDir = prevdir + ' ' + dir
            #     prevprevdir = prevdir
            #    prevdir = dir
                
            # Some directives will have arguements, so we need to identify those
            # The maxsplit arguement to the split method in dirwards is needed to
            # arrays properly. We split *only* on the first parenthesis from the left
            # hand side.
            dirwargs = dir.split('(',1)
            lenDirwargs = len(dirwargs)
            currentDir = dirwargs[0]
            dualDir = prevdir + ' ' + currentDir

            if lenDirwargs > 1: dirwargsFound = True # Boolean unused for now
            if debug:
                print 'dirwargs = ', dirwargs
                print 'dirwargs[0] = currentDir = ', currentDir
                print 'lenDirswargs = ', lenDirwargs
                print 'dualDir =', dualDir

            # identify which case we are in, only one can be true at any time
            # Need the check on dualDir equal None, because it will not exist
            # on iteration = 1.
            if dualDir != None:
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

            # Tests that only one is true with XOR, if not, skip this iteration and look for a pair
            # Otherwise, Continue
            if not (singleDirFound ^ singleDirwargsFound ^ dualDirFound ^ dualDirwargsFound):
                if debug: print "Next Iteration will check for Dual Directives Found"
                continue
            else:
                assert(singleDirFound ^ singleDirwargsFound ^ dualDirFound ^ dualDirwargsFound)
                       
            ## Code below generates the new directives depending on the value of the boolean,
            ## Probably need a function instead
            
            # (single) directive with no arguements
            if singleDirFound:
                if debug: print 'OpenACC Directive Single with no argument found'
                newDir = singleDirDict[currentDir]
                if debug: print currentDir + transitionArrow + newDir
                newLine = newLine + singleSpaceString + newDir
                
            # (single) directive with an arguement
            if (lenDirwargs > 1) and singleDirwargsFound:
                if debug: print 'OpenACC Directive Single with argument found'
                newDir = singleDirwargsDict[currentDir]
                newLine = newLine + singleSpaceString + newDir
                for j in range(1, lenDirwargs):
                    newDir = dirwargs[j]
                    if debug: print currentDir + transitionArrow + newDir
                    newLine = newLine + singleSpaceString + newDir

            # (pair) directive with no arguement
            if dualDirFound:
                if debug: print 'OpenACC Directive Dual with no arguement found'
                newDir = dualDirDict[dualDir]
                if debug: print dualDir + transitionArrow + newDir
                newLine = newLine + singleSpaceString + newDir
                
            # (pair) directive with an arguement
            if (lenDirwargs > 1) and dualDirwargsFound:
                if debug: print 'OpenACC Directive Dual with an argument'
                newDir = dualDirwargsDict[dualDir]
                newLine = newLine + singleSpaceString + newDir
                for j in range(1, lenDirwargs):
                    newDir = dirwargs[j]
                    if debug: print dualDir + transitionArrow + newDir
                    newLine = newLine + singleSpaceString + newDir

            # reset booleans for next iteration
            singleDirFound = False
            singleDirwargsFound = False
            dualDirFound = False
            dualDirwargsFound = False
            dirwargsFound = False

        # Finally we add the new line into the buffer
        newLine = newLine + '\n'
        entries.append(newLine)

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
