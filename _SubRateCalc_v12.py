"""
Script for analyzing and plotting subsidence survey data.
written by BCL

requires two subfolders in the CWD:
    - figs
    - data

rate_calcv10.py -- version 10-beta
    - 2022-01-17: added easy updated of x-tick rotation & formatter
        (xtxt_rot, date_formatter)
    - 2022-01-10: modified major/minor x-axis scale options
    - 2021-05-03: modified approach to "reset" a monument,
        now takes exact date (YYYY-MM-DD)
        rather than only a year.  This allows for two surveys in the same year
        to distinguished between.

v11 - add plots to track flange separation on wells
v12 - dz added new reference benchmark calibration
"""
import pandas as pd
import os
import numpy as np
from matplotlib import pyplot as plt
import math
import matplotlib.dates as mdates
import statsmodels.formula.api as sm
from statsmodels.sandbox.regression.predstd import wls_prediction_std
# =============================================================================
# BAYOU CHOCTAW - SUBSIDENCE
# 2022-09-20
# =============================================================================
filename = 'BayouChoctaw_SurveySummary_2024FA.xlsx'
save_as = '2024F'
plot_fit = True
plot_caliper = True
SAVE_FIG = True
SAVE_DATA = True
New_RBenchmark=False # dz:Set a new reference benchmark
vshift=0.042  # shift the 'Level Survey'further away
##############################################################################
# IDENTIFY WORKSHEETS TO BE LOADED AND 'RESET' DATES
##############################################################################
worksheet_list = [
    '2024B_rBM01','2024A_rBM01','2023B_rBM01',
    '2023A_rBM01','2022B_rBM01','2022A_rBM01',
    '2021B_rBM01','2021A_rBM01','2020B_rBM01',
    # '2020B','2020A','2019A','2018B', '2018A',
    # '2017B','2017A','2016B','2016A', '2015B',
    # '2015A','2014', '2013B','2013A', '2012',
    ]


#-- Survey data must have been aquired for well during "min_survey" of the years
#-- included in this date rate
min_survey = 3  # minimum number of consecutive surveys (need 2)
min_year = [2024, 2022]  # actual years that surveys took place - from: excel_date

#-- identifies which surveys will be included in the fit data--
surv_num = [
            23, 22, 21,20,19,18,17,16,151,
            # 15, 14,13,12,11,10,9,8,7,6,5,4,3,2,1
            ]  # from: survey_count

# define when data point was reset
reset_df = pd.DataFrame(
    {"map_id":  [
        # 'BM01',
        # 'W29'
        ],
     "reset_date":[
         # '2019-12-19',
         # '2020-06-25'
         ]
     })  # map_id & date - earlier survey values will be dropped
##############################################################################
# COORDINATES MUST MATCH THE COLUMN HEADER VALUES IN THE XLS FILE
#############################################################################
# FANNETT IS NAD83 TX SC
coord_east = 'nad83_easting_ft'
coord_north = 'nad83_northing_ft'

##############################################################################
# FORMATTING THE OUTPUT PLOTS
# fixed_y_axis_scale -> vertical scale is constant for all plots
# span0 -> fixed span of the vertical scale
##############################################################################
add_rate = True  # inclues rate in legend
fixed_y_axis_scale = True
fixed_x_axis_scale = True
#######################################################
#  only if fixed_x_axis_scale = True
xmajor =int(1)  # number of years for major x-axis interval
xminor = [1,7]  # month(s) for minor x-axis tick
#######################################################

plot_survey_tolerance = True
survey_tol = 0.01  # feet
plot_pred_std = False
h_space = 2  # horizontal spacing
v_space = 1  # vertical spacing between figures
fig_width = 6.5 # figure width in inches
fig_height = 9 # figure height in inches
fig_row = 4 # number of rows
fig_col = 3 # number of columns
plot_num = 12  # plots per page
fnt_sz = 6 # font size
span0 = .1  # DIFFERENCE BETWEEN ymin AND ymax IN PLOTS
date_formatter = '%Y-%m'
xtxt_rot = 45   # rotate the tick to a degree
##############################################################################
# choose the type of model to fit the data with
 # 1=>linear, 2=> nonlinear (quadratic), 3=> power: z=a * t^b
##############################################################################
fit_type = 1
# date that rate data is determined, only matters for nonlinear fit
# used when fit_type=2
eval_dat = 44197.  # Jan 1, 2021

##############################################################################
# FOR MODIFYIN RATES BASED ON GPS SURVEYS
# CURRENT IMPLEMENTAITON IS only for "fit_type = 1" (linear)
##############################################################################
adj_slope_inyr = -0.0  # in/yr
adj_slope_ftyr = adj_slope_inyr / 12  # ft/yr

##############################################################################
##############################################################################
# NO USER INPUT BELOW
##############################################################################
##############################################################################

current_dir = os.getcwd()
load_path = os.path.join('./data', filename) # ../ return to upper level to grab filename
save_figs = os.path.join(current_dir, "figs")

print("LOAD PATH: " + load_path)

if fit_type == 1:
    save_file = os.path.join(current_dir, "data", save_as + '_rates_lin.csv')
elif fit_type == 2:
    save_file = os.path.join(current_dir, "data", save_as + '_rates_nonlin.csv')
elif fit_type == 3:
    save_file = os.path.join(current_dir, "data", save_as + '_rates_log.csv')
fig_type = '.png'
load_file_type = '.csv'

# load excel worksheet with survey data
xl = pd.ExcelFile(load_path)

#----------------------------------------------------------

# List to store individual DataFrames
dfs = []    

for worksheet in worksheet_list:
    df = xl.parse(worksheet)
    print("imported worksheet name: " + worksheet)
    dfs.append(df)

# Concatenate the list of DataFrames into a single DataFrame
raw_data = pd.concat(dfs, ignore_index=True)


#---------------------------------------------------------
# drop columns that aren't used
raw_data.drop(['survey_id',
               'monument_operator',
               'monument_API',], axis=1, inplace=True)

# convert time to better date format
raw_data['date'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(raw_data.excel_date_num, 'D')
raw_data['year'] = pd.DatetimeIndex(raw_data['date']).year

reset_df['reset_datetime'] = pd.to_datetime(reset_df['reset_date'])

# ------------------- CHECK RAW DATA -----------------------

check = raw_data.loc[raw_data['map_id'] == 'DS12'] # UserInput, set a map_id to check data import
print(' --- RAW DATA CHECK ---')
print(check)
# ------------------- CHECK RAW DATA -----------------------

for j in reset_df.index:
    drop_index = raw_data[(raw_data['map_id']==reset_df['map_id'][j]) &
                 (raw_data['excel_date']<reset_df['reset_datetime'][j])].index
    print("----------------------------------------")
    print("----------Dropped Durint RESET----------")
    print(reset_df['map_id'][j])
    print(reset_df['reset_datetime'][j])
    print(drop_index)
    print("----------------------------------------")
    raw_data.drop(index=drop_index, inplace=True)

# # drop data prior to defined reset dates
# for j in reset_df.index:
#     # reset_year = reset_df['reset_yr'][j]
#     # reset_name = reset_df['map_id'][j]
#     for i in raw_data.index:
#         # year = raw_data['year'][i]
#         # name = raw_data['map_id'][i]
#         if reset_name == name:
#             if math.isnan(year) == False:
#                 if int(reset_year) > int(year):
#                     raw_data.drop(i, inplace=True)
#                     # print(name)
# refine data to only use that with recent and consecutive surveys
print('----- REQUIREMENT TO BE INCLUDED IN ANALYSIS -------')
print('At least ' + str(min_survey) + ' years within the years:' + str(min_year))
print('-----------------------------------------------------')

# check minimum year requirements
min_year_req = raw_data[raw_data.year.isin(min_year)].map_id
print('----- REQUIREMENT OF MINIMUM YEAR -------')
print(min_year_req)
# print('At least ' + str(min_survey) + ' years within the years:' + str(min_year))
print('-----------------------------------------------------')

raw_data = raw_data[raw_data.map_id.isin(min_year_req)]
fit_data = raw_data[raw_data['survey_count'].isin(surv_num)].dropna(subset=['final_elevation_ft'])

plot_cnt = raw_data.groupby('map_id').size().reset_index(name='counts')
fit_cnt = fit_data.groupby('map_id').size().reset_index(name='counts')

dropped_data = fit_cnt[fit_cnt.counts < min_survey]

# ----------- CHECK DROPPED DATA --------------
print(" ------------ START Dropped Data -------------- ")
print(dropped_data["map_id"])
print(" ------------ END Dropped Data -------------- ")
# ----------- CHECK DROPPED DATA --------------

# ----------- CHECK NUMBER OF SURVEYS FOR EACH MONUMENT -------
print(" ------------ START survey count -------------")
print(fit_cnt)
print(" ------------ END survey count -------------")
# ----------- CHECK NUMBER OF SURVEYS FOR EACH MONUMENT -------

# DROP DATA WITH NOT ENOUGH CONSECUTIVE SURVEYS
plot_cnt = plot_cnt.drop(plot_cnt[plot_cnt.counts < min_survey].index)
fit_cnt = fit_cnt.drop(fit_cnt[fit_cnt.counts < min_survey].index)

plot_data = raw_data.loc[raw_data['map_id'].isin(plot_cnt['map_id'])]
fit_data = fit_data.loc[fit_data['map_id'].isin(fit_cnt['map_id'])]



plot_group = plot_data.groupby('map_id')







#%%----------------------------dz: Filter well survey---------------------------
if New_RBenchmark:
    
    # Create an empty dictionary to store survey_count, BM01_values, SM04_values, and differences
    cali_dict = {'survey_count': [], 'BM01_values': [], 'SM04_values': [], 'difference': []}
    
    # Extract relevant groups
    SM04 = plot_group.get_group('SM04')
    BM01 = plot_group.get_group('BM01')
    
    # Iterate over survey counts in BM01
    for survey in BM01['survey_count']:
        BM01_values = BM01[BM01['survey_count'] == survey]['final_elevation_ft'].values
        SM04_values = SM04[SM04['survey_count'] == survey]['final_elevation_ft'].values
        difference = BM01_values - SM04_values
     
        # Append to the cali_dict
        cali_dict['survey_count'].append(int(survey))
        cali_dict['BM01_values'].append(BM01_values[0] if len(BM01_values) > 0 else None)
        cali_dict['SM04_values'].append(SM04_values[0] if len(SM04_values) > 0 else None)
        cali_dict['difference'].append(difference[0] if len(difference) > 0 else None)
    
    # Create a new dataframe from the cali_dict
    cali_df = pd.DataFrame(cali_dict)
    
    # Display the result dataframe
    print(cali_df)    
     
          
    # Create a mapping dictionary from df1
    
    mapping_dict = dict(zip(cali_df['survey_count'], cali_df['difference']))   
       
    plot_data['final_elevation_ft'] +=plot_data['survey_count'].map(mapping_dict)    
    fit_data['final_elevation_ft'] +=fit_data['survey_count'].map(mapping_dict)   
        
    plot_group = plot_data.groupby('map_id')   
    
#-------------------------------dz: end calibration-----------------------------


#%%
fit_group = fit_data.groupby('map_id')
print(fit_group)

if fit_type == 1:  # linear fit
    formula ='final_elevation_ft ~ excel_date_num'
    fit = fit_group.apply(lambda dummy: sm.ols(formula=formula, data=dummy).fit())  # ordinarly linear regression
elif fit_type == 2:  # quadratic fit
    formula='final_elevation_ft ~ excel_date_num + I(excel_date_num**2)'
    fit = fit_group.apply(lambda dummy: sm.ols(formula=formula, data=dummy).fit())  #
elif fit_type == 3:
    formula = 'ln_elev ~ ln_date'
    try:
        fit = fit_group.apply(lambda dummy: sm.ols(formula=formula, data=dummy).fit())  #
    except: ValueError

# ------------ CHECK FIT ------------------
  # evaluation "fit" object:  dir(fit['MapID'])
# out = fit['CO04']
# print(out.summary())
# SLOPE = fit['CAV04'].nobs
# b = fit['BMN01'].params[1]
# t = np.log(np.linspace(42000, 43000))
# z = a * t ** b
# ln_date = fit_group.get_group('BMN01')['ln_date']
# fit_z = np.exp(a) * np.exp(ln_date)**b
# ------------ CHECK FIT ------------------

location = pd.DataFrame({'map_id': fit_data['map_id'],
                         'easting_ft':fit_data[coord_east],
                         'northing_ft':fit_data[coord_north]})
location = location.drop_duplicates()
indexed_location = location.set_index('map_id')

col = [
    'rate_in_per_yr',
    'rate_ft_per_yr',
    'accel_in_per_yr2',
    'count',
    'SE_A',
    'SE_B',
    'pval_A',
    'pval_B',
    'f_pvalue',
    'tval_A',
    'tval_B',
    'fval',
    'condition_number',
    'conf_int_LB',
    'conf_int_UB',
    'rsquared',
    'easting_ft',
    'northing_ft',
    ]

out_df = pd.DataFrame(index=fit.index, columns=col)
for i in fit.index:
    if eval_dat == 0:
        eval_dat = fit_group.get_group(i)['excel_date_num'].max(skipna=True)
    if fit_type == 1:
        out_df['rate_ft_per_yr'][i] = fit[i].params.iloc[1] * 365.25 + adj_slope_ftyr
        out_df['rate_in_per_yr'][i] = fit[i].params.iloc[1] * 365.25 * 12 + adj_slope_inyr
        out_df['accel_in_per_yr2'][i] = 0.0
    elif fit_type == 2:
        rate_a_ft_day = fit[i].params[1]
        rate_b_ft_day = 2 * fit[i].params[2] * eval_dat
        out_df['rate_ft_per_yr'][i] = (rate_a_ft_day + rate_b_ft_day) * 365.25 + adj_slope_ftyr
        out_df['rate_in_per_yr'][i] = (rate_a_ft_day + rate_b_ft_day) * 365.25 * 12 + adj_slope_inyr
        out_df['accel_in_per_yr2'][i] = 2 * fit[i].params[2] * 12
    elif fit_type == 3:
        a = np.exp(fit[i].params[0])
        b = fit[i].params[1]
        zdot_ft_day = a * b * eval_dat **(b - 1)
        zdotdot_ft_day2 = a * b * (b - 1) * eval_dat**(b - 2)
        out_df['rate_ft_per_yr'][i] = zdot_ft_day * 365.25 + adj_slope_ftyr
        out_df['rate_in_per_yr'][i] = zdot_ft_day * 365.25 * 12 + adj_slope_inyr
        out_df['accel_in_per_yr2'][i] = zdotdot_ft_day2 * 365.25 * 12

    conf_int = fit[i].conf_int(alpha=0.05)  # 95% confidence interval
    if fit_type == 3:
        conf_int_LB = np.exp(conf_int[0].ln_date) * 365.25 * 12
        conf_int_UB = np.exp(conf_int[1].ln_date) * 365.25 * 12
        out_df['conf_int_LB'][i] = conf_int_LB
        out_df['conf_int_UB'][i] = conf_int_UB
    else:
        conf_int_LB = conf_int[0].excel_date_num * 365.25 * 12
        conf_int_UB = conf_int[1].excel_date_num * 365.25 * 12
        out_df['conf_int_LB'][i] = conf_int_LB
    out_df['conf_int_UB'][i] = conf_int_UB
    out_df['count'][i] = fit[i].nobs
    out_df['SE_A'][i] = fit[i].bse.iloc[1]
    out_df['pval_A'][i] = fit[i].pvalues.iloc[1]
    out_df['tval_A'][i] = fit[i].tvalues.iloc[1]
    out_df['condition_number'][i] = fit[i].condition_number
    out_df['rsquared'][i] = fit[i].rsquared
    out_df['fval'][i] = fit[i].fvalue
    out_df['f_pvalue'][i] = fit[i].f_pvalue
    out_df['easting_ft'][i] = indexed_location.loc[i].iloc[0]
    out_df['northing_ft'][i] = indexed_location.loc[i].iloc[1]
    if fit_type == 2:
        out_df['SE_B'][i] = fit[i].bse.iloc[2]
        out_df['pval_B'][i] = fit[i].pvalues.iloc[2]
        out_df['tval_B'][i] = fit[i].tvalues.iloc[2]
    if fit_type == 3:
        out_df['SE_B'][i] = fit[i].bse.iloc[0]
        out_df['pval_B'][i] = fit[i].pvalues.iloc[0]
        out_df['tval_B'][i] = fit[i].tvalues.iloc[0]
    if out_df['count'][i] < 2:
        out_df['rate_ft_per_yr'][i] = 'NA'
        out_df['rate_in_per_yr'][i] = 'NA'

# # ###############################################################
# # save fit data to .csv and plot survey data versus fit
# ###############################################################
if SAVE_DATA:
    out_df.to_csv(save_file)

datemin = np.datetime64(min(fit_data['date']), 'Y')
datemax = np.datetime64(max(fit_data['date']), 'Y') + np.timedelta64(18, 'M')
#%% =============================================================================
# plot and save the figures
# =============================================================================
if SAVE_FIG:
    fig = plt.figure(figsize=(fig_width, fig_height), dpi=300,
                     constrained_layout=True)
    #fig = plt.figure(figsize=(6.5, 9),tight_layout= True, dpi=300)
    key_cnt = len(raw_data['map_id'].unique())
    plot_idx = 1
    fig_idx = 1
    col_idx = 1
    span_max = 0.0
    data_span = 0.0
    for key, grp in fit_group:
        span = span0

        if plot_idx > plot_num:  # resent plot idx value
            plot_idx = 1
            fig.tight_layout(w_pad=h_space, h_pad=v_space)
            ax_location = plt.gca().get_position().y0
            fig.suptitle("Level Survey Date", fontsize=fnt_sz + 2,
                         y=ax_location -vshift)  
            if fit_type == 1:
                fig_path = os.path.join(save_figs, save_as +
                                        'LinearSurveyAnalysis_' + str(fig_idx) + fig_type)
            elif fit_type == 2:
                fig_path = os.path.join(save_figs, save_as +
                                        'NonLinSurveyAnalysis_' + str(fig_idx) + fig_type)
            elif fit_type == 3:
                fig_path = os.path.join(save_figs, save_as +
                                        'LogSurveyAnalysis_' + str(fig_idx) + fig_type)
            print(fig_path)
            plt.savefig(fig_path)
            fig_idx += 1
            fig = plt.figure(figsize=(fig_width, fig_height), dpi=300)

        fig.add_subplot(fig_row, fig_col, plot_idx)
        print("plot: " + key)
        # plot measured elevations
        
        plt.plot(plot_group.get_group(key)['date'],
                  plot_group.get_group(key)['final_elevation_ft'],
                  linestyle='-', marker='o', label=key,
                  linewidth=0.5, markersize=2, color='C0')
        
        
            
        
        if plot_survey_tolerance:
            plt.plot(grp['date'], grp['final_elevation_ft'] + survey_tol, linestyle='None', marker='_', label='_nolegend_',
                     markersize=4, color='C0')
            plt.plot(grp['date'], grp['final_elevation_ft'] - survey_tol, '_', label='Survey Tolerance',
                     markersize=4, color='C0')
        ##########################################################
        ### CALCULATE FIT STATISTICS
        ##########################################################
        stdev, iv_l, iv_u = wls_prediction_std(fit[key], alpha=0.05)
        # --------- plot fitted results-------
        if plot_fit:
            xmin = min(grp['date'])
            xmax = max(grp['date'])
            xrng = pd.to_datetime(np.linspace(xmin.value, xmax.value))
            ymin = min(grp['excel_date_num'])
            ymax = max(grp['excel_date_num'])
            yrng = np.linspace(ymin, ymax)

            if plot_pred_std:
                plt.plot(grp['date'], iv_u, linestyle='--', label='_nolegend_',
                          color='C1')
                plt.plot(grp['date'], iv_l, linestyle='--', label='95% Confidence',
                          color='C1')

            if fit_type == 1:
                plt.plot(xrng, fit[key].params.iloc[0] + fit[key].params.iloc[1] * yrng,
                         '-', label='Linear Model (OLS)',linewidth=1, color='C1')
                if add_rate:
                    if isinstance(out_df.at[key, "rate_in_per_yr"], str):
                        plt.plot([],[],' ',label="No Rate Determined" )
                    else:
                        plt.plot([],[],' ',label="Rate: " + '%.2f' % (out_df.at[key,"rate_in_per_yr"]) + " in/yr" )
            elif fit_type == 2:
                plt.plot(xrng,
                         fit[key].params.iloc[0] + fit[key].params.iloc[1] * yrng + fit[key].params.iloc[2] * yrng**2,
                         '-', label='Nonlinear Model (OLS)',linewidth=1, color='C1')
                if add_rate:
                    if isinstance(out_df.at[key, "rate_in_per_yr"], str):
                        plt.plot([],[],' ',label="No Rate Determined" )
                    else:
                        plt.plot([],[],' ',label="Rate: " + '%.2f' % (out_df.at[key,"rate_in_per_yr"]) + " in/yr" )
            elif fit_type == 3:
                plt.plot(xrng,
                         np.exp(fit[key].params.iloc[0]) * yrng**fit[key].params.iloc[1],
                         '-', label='Exp. Model (OLS)',linewidth=1, color='C1')

        plt.legend(loc=0, fontsize=fnt_sz-1)
        plt.grid(alpha=0.2, linestyle='-')
        if col_idx == 1:   
            plt.ylabel('Elevation (feet)', fontsize=fnt_sz + 2)
        # plt.xlabel('Date', fontsize=fnt_sz)
        if fixed_x_axis_scale:
            plt.xticks(rotation=xtxt_rot, fontsize=fnt_sz-1)
            ax = plt.gca()
            ax.set_xlim(datemin, datemax)
            ax.xaxis.set_major_locator(mdates.YearLocator(xmajor))
            ax.xaxis.set_minor_locator(mdates.MonthLocator(xminor))
        else:
            plt.xticks(rotation=0, fontsize=fnt_sz-1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_formatter))
        plt.yticks(fontsize=fnt_sz-1)

        ymin, ymax = plt.ylim()
        val_span = ymax - ymin
        if val_span > data_span:
            data_span = val_span
        if val_span > span:
            span = val_span
        if fixed_y_axis_scale:
            mid = ymin + (ymax - ymin) / 2
            plt.ylim(mid - span / 2., mid + span / 2.)

        if span > span_max:
            span_max = span
        # print("span_max: {:.4}".format(span_max))

        plot_idx += 1
        col_idx += 1
        
        if col_idx > fig_col:
            col_idx = 1

    fig.tight_layout(w_pad=h_space, h_pad=v_space)
    ax_location = plt.gca().get_position().y0
    print(str(ax_location))
    print('plot idx: ' + str(plot_idx))
    print('plot idx: ' + str(math.modf(plot_idx / plot_num)))
    fig.suptitle("Level Survey Date", fontsize=fnt_sz + 2,
                 y= ax_location - vshift)
    if fit_type == 1:
        fig_path = os.path.join(save_figs, save_as +
                                'LinearSurveyAnalysis_' + str(fig_idx) + fig_type)
    elif fit_type == 2:
        fig_path = os.path.join(save_figs, save_as +
                                'NonlinSurveyAnalysis_' + str(fig_idx) + fig_type)
    elif fit_type == 3:
        fig_path = os.path.join(save_figs, save_as +
                                'LogSurveyAnalysis_' + str(fig_idx) + fig_type)
    print("-------- calc axis span ---------")
    print("User Defined Y-Axis Span (span): " + str(span0))
    print("Max Y-axis Span in Data (data_span): {:.3g}".format(data_span))
    print("---------------------------------")
    print(fig_path)
    plt.savefig(fig_path)
    
#%% =============================================================================
# plot caliper data: spacing between upper & lower parts of BHF
# =============================================================================
if plot_caliper:
    fig_caliper = plt.figure(figsize=(fig_width, fig_height), dpi=300,
                     constrained_layout=True)
    #fig = plt.figure(figsize=(6.5, 9),tight_layout= True, dpi=300)
    key_cnt = len(raw_data['map_id'].unique())
    plot_idx = 1
    fig_idx = 1
    col_idx = 1
    span_max = 0.0
    data_span = 0.0
    for key, grp in fit_group:
        if plot_data[plot_data['map_id']==key]['flange_ft'].isnull().values.all() != True:
            print('Plot Flange Data: '+ key)
            span = span0
            if plot_idx > plot_num:  # resent plot idx value
                plot_idx = 1
                fig_caliper.tight_layout(w_pad=h_space, h_pad=v_space)
                ax_location = plt.gca().get_position().y0
                fig_caliper.suptitle("Level Survey Caliper Date", fontsize=fnt_sz + 2,
                             y=ax_location - vshift)  
                fig_path = os.path.join(save_figs, save_as +
                                        'CaliperData_' + str(fig_idx) + fig_type)
                print(fig_path)
                plt.savefig(fig_path)
                fig_idx += 1
                fig_caliper = plt.figure(figsize=(fig_width, fig_height), dpi=300)
    
            fig_caliper.add_subplot(fig_row, fig_col, plot_idx)
            # plot measured elevations
            plt.plot(plot_group.get_group(key)['date'],
                     plot_group.get_group(key)['flange_ft'],
                     linestyle='-', marker='o', label=key,
                     linewidth=0.5, markersize=2, color='C0')
            
            if plot_survey_tolerance:
                plt.plot(grp['date'], grp['flange_ft'] + survey_tol, linestyle='None', marker='_', label='_nolegend_',
                         markersize=4, color='C0')
                plt.plot(grp['date'], grp['flange_ft'] - survey_tol, '_', label='Survey Tolerance',
                         markersize=4, color='C0')
            plt.legend(loc=0, fontsize=fnt_sz-1)
            plt.grid(alpha=0.2, linestyle='-')
            if col_idx == 1:   
                plt.ylabel('Flange Separation (feet)', fontsize=fnt_sz + 2)
            # plt.xlabel('Date', fontsize=fnt_sz)
            if fixed_x_axis_scale:
                plt.xticks(rotation=xtxt_rot, fontsize=fnt_sz-1)
                ax = plt.gca()
                ax.set_xlim(datemin, datemax)
                ax.xaxis.set_major_locator(mdates.YearLocator(xmajor))
                ax.xaxis.set_minor_locator(mdates.MonthLocator(xminor))
            else:
                plt.xticks(rotation=0, fontsize=fnt_sz-1)
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_formatter))
            plt.yticks(fontsize=fnt_sz-1)
    
            ymin, ymax = plt.ylim()
            val_span = ymax - ymin
            if val_span > data_span:
                data_span = val_span
            if val_span > span:
                span = val_span
            if fixed_y_axis_scale:
                mid = ymin + (ymax - ymin) / 2
                plt.ylim(mid - span / 2., mid + span / 2.)
    
            if span > span_max:
                span_max = span
            # print("span_max: {:.4}".format(span_max))
    
            plot_idx += 1
            col_idx += 1
            
            if col_idx > fig_col:
                col_idx = 1

    fig_caliper.tight_layout(w_pad=h_space, h_pad=v_space)
    ax_location = plt.gca().get_position().y0
    fig_caliper.suptitle("Level Survey Caliper Date", fontsize=fnt_sz + 2,
                 y=ax_location - vshift)  
    fig_path = os.path.join(save_figs, save_as +
                            'CaliperData_' + str(fig_idx) + fig_type)
    print(fig_path)
    plt.savefig(fig_path)
