import sys, time, random
#from numarray import *
from tables import *

class Test(IsDescription): 
    ngroup = IntCol(pos=1)
    ntable = IntCol(pos=2)
    nrow = IntCol(pos=3)
    time = Float64Col(pos=5)
    random = Float32Col(pos=4)

def createFile(filename, ngroups, ntables, nrows, complevel, complib, recsize):

    # Open a file in "w"rite mode
    fileh = openFile(filename, mode = "w")

    # Table title
    title = "PyTables Stress Test"
    
    rowswritten = 0
    for k in range(ngroups):
        # Create the group
        group = fileh.createGroup("/", 'group%04d'% k, "Group %d" % k)
        for j in range(ntables):
            # Create a table
            table = fileh.createTable(group, 'table%04d'% j, Test, title,
                                      complevel, complib, nrows)
            # Get the row object associated with the new table
            row = table.row
            # Fill the table
            for i in xrange(nrows):
                row['time'] = time.time()
                row['random'] = random.random()*40+100
                row['ngroup'] = k
                row['ntable'] = j
                row['nrow'] = i
                row.append()
		    
            rowswritten += nrows

    # Close the file (eventually destroy the extended type)
    fileh.close()
    
    return (rowswritten, table.rowsize)

def readFile(filename, recsize, verbose):
    # Open the HDF5 file in read-only mode

    fileh = openFile(filename, mode = "r")
    rowsread = 0
    ngroup = 0
    # Get a group
    for group in fileh.listNodes(fileh.root, 'Group'):
        ntable = 0
        if verbose:
            print "Group ==>", group
        for table in fileh.listNodes(group, 'Table'):
            rowsize = table.rowsize
            buffersize=table.rowsize * table._v_maxTuples
            if verbose:
                print "Table ==>", table
                print "Max rows in buf:", table._v_maxTuples
                print "Rows in", table._v_pathname, ":", table.nrows
                print "Buffersize:", table.rowsize * table._v_maxTuples
                print "MaxTuples:", table._v_maxTuples

            nrow = 0
            time_1 = 0.0
            for row in table:
                try:
                    # print "row['ngroup'], ngroup ==>", row["ngroup"], ngroup
                    assert row["ngroup"] == ngroup
                    assert row["ntable"] == ntable
                    assert row["nrow"] == nrow
                    # print "row['time'], time_1 ==>", row["time"], time_1
                    assert row["time"] >= (time_1 - 0.01)
                    assert 100 <= row["random"] <= 140
                except:
                    print "Error in group: %d, table: %d, row: %d" % \
                          (ngroup, ntable, nrow)
                    print "Record ==>", row
                time_1 = row["time"]
                nrow += 1
                    
            assert nrow == table.nrows
	    rowsread += table.nrows
            ntable += 1
        ngroup += 1
        
    # Close the file (eventually destroy the extended type)
    fileh.close()

    return (rowsread, rowsize, buffersize)

if __name__=="__main__":
    import getopt
    try:
        import psyco
        psyco_imported = 1
    except:
        psyco_imported = 0


    usage = """usage: %s [-v] [-p] [-r] [-w] [-l complib] [-c complevel] [-g ngroups] [-t ntables] [-i nrows] file
    -v verbose
    -p use "psyco" if available
    -r only read test
    -w only write test
    -l sets the compression library to be used ("zlib", "lzo", "ucl")
    -c sets a compression level (do not set it or 0 for no compression)
    -g number of groups hanging from "/"
    -t number of tables per group
    -i number of rows per table
"""
    
    try:
        opts, pargs = getopt.getopt(sys.argv[1:], 'vprwl:c:g:t:i:')
    except:
        sys.stderr.write(usage)
        sys.exit(0)

    # if we pass too much parameters, abort
    if len(pargs) <> 1: 
        sys.stderr.write(usage)
        sys.exit(0)

    # default options
    ngroups = 5
    ntables = 5
    nrows = 100
    verbose = 0
    recsize = "medium"
    testread = 1
    testwrite = 1
    usepsyco = 0
    complevel = 0
    complib = "zlib"

    # Get the options
    for option in opts:
        if option[0] == '-v':
            verbose = 1
        if option[0] == '-p':
            usepsyco = 1
        elif option[0] == '-r':
            testwrite = 0
        elif option[0] == '-w':
            testread = 0
        elif option[0] == '-l':
            complib = option[1]
        elif option[0] == '-c':
            complevel = int(option[1])
        elif option[0] == '-g':
            ngroups = int(option[1])
        elif option[0] == '-t':
            ntables = int(option[1])
        elif option[0] == '-i':
            nrows = int(option[1])
            
    # Catch the hdf5 file passed as the last argument
    file = pargs[0]

    print "Compression level:", complevel
    if complevel > 0:
        print "Compression library:", complib
    if testwrite:
	t1 = time.time()
	cpu1 = time.clock()
        if psyco_imported and usepsyco:
            psyco.bind(createFile)
	(rowsw, rowsz) = createFile(file, ngroups, ntables, nrows,
                                    complevel, complib, recsize)
	t2 = time.time()
        cpu2 = time.clock()
	tapprows = round(t2-t1, 3)
	cpuapprows = round(cpu2-cpu1, 3)
        tpercent = int(round(cpuapprows/tapprows, 2)*100)
	print "Rows written:", rowsw, " Row size:", rowsz
	print "Time writing rows: %s s (real) %s s (cpu)  %s%%" % \
              (tapprows, cpuapprows, tpercent)
	print "Write rows/sec: ", int(rowsw / float(tapprows))
	print "Write KB/s :", int(rowsw * rowsz / (tapprows * 1024))

    if testread:
	t1 = time.time()
        cpu1 = time.clock()
        if psyco_imported and usepsyco:
            psyco.bind(readFile)
        (rowsr, rowsz, bufsz) = readFile(file, recsize, verbose)
	t2 = time.time()
        cpu2 = time.clock()
	treadrows = round(t2-t1, 3)
        cpureadrows = round(cpu2-cpu1, 3)
        tpercent = int(round(cpureadrows/treadrows, 2)*100)
	print "Rows read:", rowsr, " Row size:", rowsz, "Buf size:", bufsz
	print "Time reading rows: %s s (real) %s s (cpu)  %s%%" % \
              (treadrows, cpureadrows, tpercent)
	print "Read rows/sec: ", int(rowsr / float(treadrows))
	print "Read KB/s :", int(rowsr * rowsz / (treadrows * 1024))
    

