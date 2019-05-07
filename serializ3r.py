
import click
import csv
import sys

def import_db():

    database_location = click.prompt('Please enter the location of your dump', type=str)
    
    # Read first five lines and print to user
    
    with open(database_location) as database_file:
        head = [next(database_file) for x in range(5)]
    for i in head:
        print(i)
    
    # Ask user if json, csv, or other
    
    db_type = click.prompt('Is the database in json format[1], csv format[2], or other[3]?', type=click.IntRange(1,3))
    db_types = {
        1: "Json",
        2: "CSV",
        3: "Other"
    }
    output = "The database is in " + db_types.get(db_type, "Invalid Type") + " Format"
    print(output)
    # Parse according to answer
    return db_type, database_location

def convert(db_t, db_location):

    with open(db_location) as db_file:
        if db_t == 1:
            #placeholder
        elif db_t == 2:
            #placeholder
        else:
            #placeholder

def convert_csv(db_t, db_location):
    #placeholder

def convert_json(db_t, db_location):
    #placeholder


if __name__ == '__main__':
    click.echo('Importing the database...')
    db_type, db_loc = import_db()
