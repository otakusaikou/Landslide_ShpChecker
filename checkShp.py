#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import psycopg2
import datetime
import numpy as np


def initDB(host, port, user, dbName):
    """Initialize the PostGIS database"""
    # Replace and create a new database with PostGIS extension
    print "Initialize the PostGIS database..."
    cmdStr = "psql -h %s -p %s -U %s -c \"DROP DATABASE IF EXISTS %s;\"" \
        % (host, port, user, dbName)
    os.popen(cmdStr)

    cmdStr = "psql -h %s -p %s -U %s -c \"CREATE DATABASE %s;\"" \
        % (host, port, user, dbName)
    os.popen(cmdStr)

    cmdStr = "psql -h %s -p %s -U %s -d %s -f sql/dbinit.sql" \
        % (host, port, user, dbName)
    os.popen(cmdStr)


def uploadShp(conn, csvFile, rootDir, host, port, user, dbName):
    """Upload target landslide data to database"""
    cur = conn.cursor()     # Get cursor object of database connection

    os.chdir(os.path.join(rootDir, "shp"))

    # Read information from csv file
    data = np.genfromtxt(csvFile, delimiter=",", dtype=object)
    tmpName, mapName, remarks, projDate, inputDate = map(
        lambda x: x.flatten(), np.hsplit(data, 5))
    tmpName += ".shp"

    # Open a log file for recording error messages
    log = open("../log.txt", "w")

    # Check if the shapefile exists
    for i in range(len(tmpName)):
        if not os.path.exists(tmpName[i]):
            print "Cannot find shapefile: '%s', make sure the path and file" \
                " name is correct." % tmpName[i]
            continue

        # Import shapefile to database as a template table
        sql = "DROP TABLE IF EXISTS inputData"
        cur.execute(sql)
        conn.commit()

        print "Import shapefile '%s' to database..." % tmpName[i]
        cmdStr = "shp2pgsql -s 3826 -c -D -I -W big5 %s inputData | psql -h " \
            "%s -p %s -d %s -U %s" % (tmpName[i], host, port, dbName, user)
        os.popen(cmdStr)

        # Test if the geometries is well formed
        sql = "SELECT gid, ST_IsValidReason(geom) FROM inputdata " \
            "WHERE NOT ST_IsValid(geom)"""
        cur.execute(sql)
        result = cur.fetchall()

        if len(result):
            log.write(("-" * 20) + tmpName[i] + ("-" * 20) + "\n")
            message = "\n".join(map(lambda x: "gid: %d, Reason: %s"
                                % (int(x[0]) - 1, x[1]), np.array(result)))

            log.write(message + "\n" + ("-" * 50) + "\n\n")

    log.close()

    # Remove unnecessary table
    print "Remove unnecessary table..."
    sql = "DROP TABLE IF EXISTS public.inputData"
    cur.execute(sql)
    conn.commit()


def main():
    tStart = datetime.datetime.now()

    # Define database connection parameters
    host = "localhost"
    port = "5432"
    dbName = "gis_process"
    user = "postgres"

    csvFile = "f6.csv"  # Shapefile information
    rootDir = os.getcwd()

    # Ask user whether to reinitialize the database
    flag = raw_input("Initialize database? (Y/N) ").lower()
    while flag not in ["yes", "no", "y", "n"]:
        flag = raw_input(
            "Invalid selection (You should input 'Y' or 'N') ").lower()

    if flag in ["Y", "y", "Yes", "yes"]:
        initDB(host, port, user, dbName)

    # Connect to database
    try:
        conn = psycopg2.connect("dbname='%s' user='%s' host='%s' port='%s'"
                                % (dbName, user, host, port))
    except psycopg2.OperationalError:
        print "Unable to connect to the database."
        return -1

    uploadShp(conn, csvFile, rootDir, host, port, user, dbName)
    conn.close()

    tEnd = datetime.datetime.now()
    print "Works done! It took %f sec" % (tEnd - tStart).total_seconds()

    return 0


if __name__ == '__main__':
    main()
