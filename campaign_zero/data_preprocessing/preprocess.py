import os
import glob
import csv
import sys
# import numpy as np

from collections import defaultdict
from datetime import datetime
from pprint import pprint


def preprocess_nashville(input_data_folder, output_data_folder):

    force_filename = os.path.join(input_data_folder, 'nashville_use_of_force.csv')
    assigments_filename = os.path.join(input_data_folder, 'nashville_police_assignments.csv')
    complaints_filename = os.path.join(input_data_folder, 'nashville_complaints.csv')
    
    # Extract employee and assingment information
    employee_dict = defaultdict(lambda: defaultdict(list))
    with open(assigments_filename, 'r') as openfile:
        reader = csv.reader(openfile, delimiter=',')

        # Skip Header
        next(reader)

        for row in reader:
            emp_id = row[0]
            employee_dict[emp_id]['complaint_count'] = 0
            employee_dict[emp_id]['civilian_complaint_count'] = 0
            employee_dict[emp_id]['complaint_count_assignment'] = 0
            employee_dict[emp_id]['civilian_complaint_count_assignment'] = 0
            employee_dict[emp_id]['gender'] = row[-2]
            employee_dict[emp_id]['race'] = row[-3]
            employee_dict[emp_id]['bureaus'] += [row[1]]
            employee_dict[emp_id]['divisions'] += [row[2]]
            employee_dict[emp_id]['sections'] += [row[3]]
            employee_dict[emp_id]['missing'] = False
            employee_dict[emp_id]['hire_date'] = datetime.strptime(row[-4][:-4], '%Y-%m-%d %H:%M:%S')
            employee_dict[emp_id]['start_dates'] += [datetime.strptime(row[-6][:-4], '%Y-%m-%d %H:%M:%S')]
            employee_dict[emp_id]['experiences'] += [(employee_dict[emp_id]['start_dates'][-1] - employee_dict[emp_id]['hire_date']).days]
            employee_dict[emp_id]['max_experience'] = (datetime(2019, 1, 1) - employee_dict[emp_id]['hire_date']).days
            employee_dict[emp_id]['ages'] += [int(row[-1])]

            if 'max_age' not in employee_dict[emp_id].keys():
                employee_dict[emp_id]['max_age'] = int(row[-1])
            else:
                employee_dict[emp_id]['max_age'] = max(int(row[-1]), employee_dict[emp_id]['max_age'])

            end_date = row[-5][:-4]
            if end_date == '3000-01-01 00:00:00':
                # Adjust this to time data was retrieved.
                # employee_dict[emp_id]['end_dates'] += [datetime.today()]
                if len(employee_dict[emp_id]['end_dates']) == 0:
                    employee_dict[emp_id]['end_dates'] += [datetime(2019, 1, 1)]
                else:
                    employee_dict[emp_id]['end_dates'] += [employee_dict[emp_id]['end_dates'][-1]]
            else:
                employee_dict[emp_id]['end_dates'] += [datetime.strptime(row[-5][:-4], '%Y-%m-%d %H:%M:%S')]

    # Derived Statistics
    for key, item in employee_dict.items():
        employee_dict[key]['start_date'] = employee_dict[key]['start_dates'][0]
        employee_dict[key]['end_date'] = employee_dict[key]['end_dates'][-1]
        employee_dict[key]['days_assigned'] = (employee_dict[key]['end_dates'][-1] - employee_dict[key]['start_dates'][0]).days + 1
        employee_dict[key]['active'] = employee_dict[key]['end_dates'][-1].date() >= datetime(2019, 1, 1).date()
        switches = 0
        for idx, section in enumerate(employee_dict[key]['sections']):
            if idx == 0:
                current_section = section
            else:
                if section != current_section:
                    switches += 1
                current_section = section
        employee_dict[key]['switches'] = switches

    # Create Division Change Dates

    # Extract complaint information
    complaint_dict = defaultdict(lambda: defaultdict(int))
    with open(complaints_filename, 'r') as openfile:
        reader = csv.reader(openfile, delimiter=',')
        original_header = next(reader)

        for row in reader:
            emp_id = row[6]
            complaint_id = row[9]
            complaint_dict[complaint_id]['emp_id'] = emp_id
            complaint_dict[complaint_id]['original_data'] = row
            employee_dict[emp_id]['first_name'] = row[4]
            employee_dict[emp_id]['last_name'] = row[3]
            employee_dict[emp_id]['full_name'] = row[4] + ' ' + row[3]
            complaint_dict[complaint_id]['gender'] = employee_dict[emp_id]['gender']
            complaint_dict[complaint_id]['race'] = employee_dict[emp_id]['race']
            date = datetime.strptime(row[2], '%B %d, %Y')

            previous_end_date = datetime(1900, 1, 1)
            time_fields = ['bureau', 'division', 'section', 'age', 'experience']
            for date_index, end_date in enumerate(employee_dict[emp_id]['end_dates']):
                if date_index == 0 and date < end_date:
                    for field in time_fields:
                        complaint_dict[complaint_id][field] = 'Unassigned'
                    complaint_dict[complaint_id]['during_assignment'] = False
                    break
                if date <= end_date and date > previous_end_date:
                    for field in time_fields:
                        complaint_dict[complaint_id][field] = employee_dict[emp_id][field + 's'][date_index]
                    complaint_dict[complaint_id]['during_assignment'] = True
                    break
                if date_index == len(employee_dict[emp_id]['end_dates']) - 1:
                    for field in time_fields:
                        complaint_dict[complaint_id][field] = employee_dict[emp_id][field + 's'][-1]
                    complaint_dict[complaint_id]['during_assignment'] = False
                    break
                previous_end_date = end_date

            for key in ['bureau', 'division', 'section']:
                if key not in complaint_dict[complaint_id].keys():
                    complaint_dict[complaint_id][key] = ''

            if 'complaint_count' not in employee_dict[emp_id]:
                employee_dict[emp_id]['civilian_complaint_count'] = 1
                employee_dict[emp_id]['complaint_count'] = 1
                employee_dict[emp_id]['civilian_complaint_count_assignment'] = 1
                employee_dict[emp_id]['complaint_count_assignment'] = 1
                employee_dict[emp_id]['missing'] = True
            else:
                if row[-4] == 'Citizen':
                    employee_dict[emp_id]['civilian_complaint_count'] += 1
                    if complaint_dict[complaint_id]['during_assignment']:
                        employee_dict[emp_id]['civilian_complaint_count_assignment'] += 1
                employee_dict[emp_id]['complaint_count'] += 1
                if complaint_dict[complaint_id]['during_assignment']:
                    employee_dict[emp_id]['complaint_count_assignment'] += 1

    # Derived Statistics
    copy_employee_dict = employee_dict.copy()
    for key, item in copy_employee_dict.items():
        if employee_dict[key]['missing']:
            for field in ['complaint_per_day', 'civilian_complaint_per_day',
                    'civilian_complaint_per_year', 'complaint_per_year',
                    'complaint_assignment_per_day', 
                    'complaint_assignment_per_year',
                    'civilian_complaint_assignment_per_day',
                    'civilian_complaint_assignment_per_year']:
                employee_dict[key][field] = 'null'
        else:
            for metric in ['complaint_count', 'civilian_complaint_count', 
                    'complaint_count_assignment', 
                    'civilian_complaint_count_assignment', 'switches']:
                # print(employee_dict[key][metric])
                employee_dict[key][f'{metric}_per_day'] = employee_dict[key][metric] / employee_dict[key]['days_assigned']
                employee_dict[key][f'{metric}_per_year'] = employee_dict[key][f'{metric}_per_day'] * 365
    del(copy_employee_dict)

    # Create extended complaints
    complaints_plus = os.path.join(output_data_folder, 
        'nashville_complaints_extended.csv')
    with open(complaints_plus, 'w', newline='') as outfile:
        writer = csv.writer(outfile, delimiter=',')
        header = original_header + ['age', 'gender', 'race', 'bureau', 
            'division', 'section', 'experience', 'missing',
            'active', 'days_assigned', 
            'complaint_count_assignment', 
            'civilian_complaint_count_assignment',
            'complaint_assignment_per_day', 'complaint_assignment_per_year',
            'civilian_complaint_assignment_per_day',
            'civilian_complaint_assignment_per_year',
            'complaint_count', 
            'civilian_complaint_count', 'complaint_per_day', 
            'complaint_per_year', 'civilian_complaint_per_day', 
            'civlian_complaint_per_year', 'during_assignment']
        writer.writerow(header)

        for complaint_id, item in complaint_dict.items():
            emp_id = item['emp_id']
            output_row = item['original_data']
            output_row += [item['age'], item['gender'], item['race'],
                item['bureau'], item['division'], item['section'],
                item['experience']]
            output_row += [employee_dict[emp_id]['missing'],
                employee_dict[emp_id]['active'],
                employee_dict[emp_id]['days_assigned'],
                employee_dict[emp_id]['complaint_count_assignment'],
                employee_dict[emp_id]['civilian_complaint_count_assignment'],
                employee_dict[emp_id]['complaint_assignment_per_day'],
                employee_dict[emp_id]['complaint_assignment_per_year'],
                employee_dict[emp_id]['civilian_complaint_assignment_per_day'],
                employee_dict[emp_id]['civilian_complaint_assignment_per_year'],
                employee_dict[emp_id]['complaint_count'],
                employee_dict[emp_id]['civilian_complaint_count'],
                employee_dict[emp_id]['complaint_per_day'],
                employee_dict[emp_id]['complaint_per_year'],
                employee_dict[emp_id]['civilian_complaint_per_day'],
                employee_dict[emp_id]['civilian_complaint_per_year'],
                item['during_assignment']]
            writer.writerow(output_row)

    # Create cop spreadsheet
    cop_list = os.path.join(output_data_folder, 
        'nashville_cop_details.csv')

    with open(cop_list, 'w', newline='') as outfile:
        writer = csv.writer(outfile, delimiter=',')
        header = ['emp_id', 'name', 'first_name', 'last_name', 'max_age',
            'gender', 'race', 'missing',
            'start_date', 'end_date', 'hire_date', 'max_experience', 
            'days_assigned', 'switches', 'switches_per_day',
            'switches_per_year', 'complaint_count_assignment', 
            'civilian_complaint_count_assignment',
            'complaint_count_assignment_per_day', 
            'complaint_count_assignment_per_year',
            'civilian_complaint_count_assignment_per_day',
            'civilian_complaint_count_assignment_per_year',
            'complaint_count',
            'civilian_complaint_count', 'complaint_count_per_day', 
            'complaint_count_per_year',
            'civilian_complaint_count_per_day', 
            'civilian_complaint_count_per_year']
        writer.writerow(header)

        for emp_id, item in employee_dict.items():
            output_row = [emp_id]
            for field in header[1:]:
                output_row += [item[field]]
            writer.writerow(output_row)

    # Create model spreadsheet.
    model_spreadsheet = os.path.join(output_data_folder,
        'nashville_model_formatted.csv')

    # Start Assignments January 1, 2009
    # End Complaints July 18, 2018
    period_start_date = datetime(2009, 1, 1)
    period_end_date = datetime(2018, 7, 18)
    time_index = 0
    gender_dict = {'F': 0, 'M': 1}
    race_dict = {'A': 0, 'B': 1, 'I': 2, 'T': 3, 'W': 4, 'H': 5}
    model_header = ['police_id', 'time', 'section', 'race', 
        'gender', 'age', 'experience']
    model_dict = {}
    while period_start_date < period_end_date:

        return

    return


def test_analysis():

    import statsmodels.api as sm
    import pandas as pd
    pd.set_option('display.max_rows', 1000)
    # import statsmodels.formula.api as smf
    data = sm.datasets.get_rdataset("dietox", "geepack").data
    pprint(data)
    print(data.dtypes)
    return


if __name__ == '__main__':

    # Nashville
    input_dir = '../../../data/original/nashville'
    output_dir = '../../../data/processed/nashville'
    preprocess_nashville(input_dir, output_dir)
    # test_analysis()

    pass