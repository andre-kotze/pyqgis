from exif import (Image as exif, DATETIME_STR_FORMAT)
import piexif
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import numpy as np
import os
from datetime import (datetime, timedelta)
import time
import sys

settings = 'C:/Users/User/Desktop/SHARE/IMDH App Settings/'
try:
    with open(settings + 'logo/Doh_spaced.txt','r') as title:
        print(title.read())
    time.sleep(2)
    with open(settings + 'PhotoRename/instructions.txt','r') as instr:
        print('\n', instr.read())
    concessions = pd.read_csv(settings + 'PhotoRename/concessions.csv')
except Exception as e:
    print(e, '\n\nError reading from settings directory:\n', settings, 'Exiting . . .')
    sys.exit(0)

valid = concessions['Concession'].values.tolist()
print('Currently supports:', ', '.join(valid))
concession = (input('Enter Concession name:\t')).upper()
while concession not in valid:
    concession = input('Try again..\nEnter Concession name:\t')
path = concessions.loc[concessions['Concession'] == concession, 'PathToPhotos'].iloc[0]
sl = concessions.loc[concessions['Concession'] == concession, 'PathToScreenlog'].iloc[0]
if not os.path.exists(path) and os.path.exists(sl) and os.path.exists(settings):
    print('File/Folder not found. Check:\n',)

# GENBOARD dims:
x , y = 800, 600 
def fontsize(length):
    fs = -10 * length +220
    return fs

def continue_prompt(msg='Continue? [Y/N] '):
    proceed = ''
    while proceed != 'Y':
        proceed = input(msg)
        if proceed.upper() == 'N':
            sys.exit(0)
        elif proceed.upper() == 'Y':
            break
        else:
            print('Epic fail! Please respond with Y or N, not "' + proceed + '"')
            time.sleep(1.2)

# FIND EARLIEST DATETIME IN PHOTOS, AND CREATE DF WITH IMAGE FILES AND DATESTAKEN
def check_photos():
    datelist = []
    photoslist = []
    print('\nChecking Photos in', path, '. . .', end='\t\t', flush=True)
    files = os.listdir(path)
    if len(files) == 0:
        print('\n\nNO FILES FOUND')
        exit = input("\nPress Enter to exit")
        sys.exit(0)
    for f in files:
        if '.JPG' in f:
            photoslist.append(f)
            with open(path + f, 'rb') as img:
                image = exif(img)
                td = image.datetime
                datetaken = datetime.strptime(td,"%Y:%m:%d %H:%M:%S")
                datelist.append(datetaken)
    if len(photoslist) == 0:
        print('\n\nNO .JPG FILES FOUND')
        exit = input("\nPress Enter to exit")
        sys.exit(0)
    data = {'Photo':photoslist, 'Date_Taken':datelist}
    photodf = pd.DataFrame(data)
    # CONVERT DATETAKENS FROM TIMESTAMP TO PY_DATETIME FORMAT
    for i, p in photodf.iterrows():
        p['Date_Taken'] = p['Date_Taken'].to_pydatetime(warn=False)
    earliest = min(datelist)
    earliest = datetime.date(earliest)
    print('[OK]')
    print('Photos found in folder:', len(datelist), '\nDate of earliest photo in folder:', earliest)
    return photodf, earliest

# READ ENTIRE SCREENLOG
def get_first_seq(earliest):
    print('\nLoading Screenlog . . .', end='\t\t\t', flush=True)
    cp = datetime.now()
    try:
        screenlog = pd.read_excel(
            sl, 
            engine = 'pyxlsb', 
            usecols = [
                'Seq',
                'Sample_ID', 
                'Start_Date',
                'Start_Time'
            ])
    except Exception as e:
        print(e, '\n\nError reading Screenlog (' + sl + ')\nExiting . . .')
        sys.exit(0)  
    # DROP ROWS WITH NULL TIME DATA
    screenlog.dropna(subset=['Start_Time'], inplace=True)
    screenlog.reset_index(inplace=True, drop=True)
    # CONVERT DATE FROM FLOAT TO TIMESTAMP FORMAT
    screenlog['Start_Date'] = pd.TimedeltaIndex(
        screenlog['Start_Date'], 
        unit = 'd') + datetime(1899, 12, 30)
    print('\t\t[OK]')
    # FIND SEQUENCE NUMBER OF FIRST SAMPLE ON EARLIEST DATE
    for i, c in screenlog.iterrows():
        day = datetime.date(c['Start_Date'])
        if day == earliest:
            firstsample_seq = int(c['Seq'])
            break
    dur = datetime.now() - cp
    dur = dur.seconds + (dur.microseconds / 1000000)
    print('(Read Screenlog took', round(dur, 2), 'seconds)\n\n')
    print('Seq of first sample on', str(earliest) + ':', str(firstsample_seq))
    return screenlog, firstsample_seq

# RELOAD SCREENLOG, SKIPPING IRRELEVANT ROWS
def trim_screenlog_at_seq(screenlog, seq):
    print('\nLoading Screenlog from Seq', str(seq), '. . .', end='\t\t\t', flush=True)
    screenlog.drop(screenlog[screenlog.Seq < seq].index, inplace = True) # filter in place
    screenlog.loc[:, 'Start_Time'] = pd.TimedeltaIndex(screenlog.loc[:, 'Start_Time'], unit = 'd') # CONVERT DATE AND TIME FROM FLOAT TO TIMESTAMP FORMAT (date AND time)
    screenlog.loc[:, 'Start_Datetime'] = (screenlog.loc[:, 'Start_Date'] + screenlog.loc[:, 'Start_Time']) # MERGE START DATE AND TIME INTO..........:  "DATETIME"
    del screenlog['Start_Date'], screenlog['Start_Time']    # REMOVE NOW-DEFUNCT COLUMNS
    screenlog.reset_index(inplace=True, drop=True)
    for i, sample in screenlog.iterrows():
        sample['Start_Datetime'] = sample['Start_Datetime'].to_pydatetime(warn=False)    # CONVERT DATETIMES FROM TIMESTAMP TO PY_DATETIME FORMAT
    # SET END TIME AS NEXT SAMPLE'S START TIME
    for i in range(0, len(screenlog) - 1):
        screenlog.loc[i, 'End_Datetime'] = screenlog.loc[i + 1, 'Start_Datetime'] # SET END TIME AS NEXT SAMPLE'S START TIME (FINAL SAMPLE END TIME WILL BE NULL)
    print('[OK]')
    print(len(screenlog), 'samples loaded from Screenlog')
    return screenlog

# ITERATE THROUGH SAMPLES, TO COMPILE LISTS OF JPGs PER SAMPLE, ADD LIST IN DATAFRAME
def sort_photos(screenlog, photodf):
    print('\nComparing', len(screenlog), 'sample_IDs and', len(photodf), 'files', end='\t\t\t', flush=True)
    photoslist = []
    for i, sample in screenlog.iterrows(): 
        sample['End_Datetime'] = sample['End_Datetime'].to_pydatetime(warn=False)
        samplephotos = []
        for i, ph in photodf.iterrows():
            if pd.isnull(sample['End_Datetime']) & (ph['Date_Taken'] > sample['Start_Datetime']):
                samplephotos.append(ph['Photo'])
            elif (ph['Date_Taken'] > sample['Start_Datetime']) & (ph['Date_Taken'] < sample['End_Datetime']):
                samplephotos.append(ph['Photo'])
            else:
                pass
        photoslist.append(samplephotos) #samplephotos is a list of JPGs for one sample
    #photoslist is the list of samplelists
    print('[OK]\n')
    return photoslist

# FUNCTION TO GENERATE NAMEBOARDS
def genboard(sample_id, datetaken): # sample_id = str, datetaken = pydatetime
    img = Image.new('RGB', (x, y), color = (255, 255, 255))
    size = fontsize(len(sample_id))
    fnt = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', size)
    lfnt = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 140)
    d = ImageDraw.Draw(img)
    w, h = fnt.getsize(sample_id)
    cw, ch = lfnt.getsize(concession)
    d.text(((x-cw)/2, (y/6.6)), concession, font = lfnt, fill = (0, 0, 0))
    d.text(((x-w)/2, (y/2)), sample_id, font = fnt, fill = (0, 0, 0))
    boardfname = (concession + '_' + sample_id + '_01.JPG')
    bdate = datetaken
    imgdate = bdate.strftime(DATETIME_STR_FORMAT)
    exif_dict = {'0th':{306:imgdate},'Exif':{36867:imgdate, 36868:imgdate}}
    exif_bytes = piexif.dump(exif_dict)
    img.save(path + boardfname,exif=exif_bytes)
    mtime = time.mktime(bdate.timetuple())
    os.utime(path + boardfname,(mtime,mtime))
    return(boardfname, bdate)

# --- ITERATE THROUGH LIST OF LISTS, RENAMING FILES:
def rename(screenlog, photoslist):
    print('Renaming Photos . . .')
    renamelist = []
    genlist = []
    for ind, item in enumerate(photoslist): # LIST OF LISTS (BY SAMPLE)
        sampleid = screenlog.loc[ind,'Sample_ID']
        dateinfo = screenlog.loc[ind,'Start_Datetime']
        for index, data in enumerate(item): # LIST OF JPGs FOR ONE SAMPLE ('item')
            if index == 0:
                nb, newdate = genboard(sampleid, dateinfo)
                genlist.append(nb)
                print('\n-Nameboard generated as', nb)#, '\t\t\twith time of', newdate)
            filename = (concession + '_' + sampleid + '_' + f'{(index + 2):02d}' + '.JPG')
            os.rename(path + data, path + filename)
            print(data + ' renamed to ' + filename)
            renamelist.append(filename)
    print('\n[Finished]\n\n', str(len(renamelist)), 'photos renamed\n', str(len(genlist)), 'nameboards generated')

# MAIN
def main():
    photodf, earliest = check_photos()
    continue_prompt()
    screenlog, seq1 = get_first_seq(earliest)
    continue_prompt()
    screenlog = trim_screenlog_at_seq(screenlog, seq1)
    prompt = 'Compare ' + str(len(screenlog)) + ' sample_IDs and ' + str(len(photodf)) + ' files? [Y/N] '
    continue_prompt(prompt)
    cp = datetime.now()
    photoslist = sort_photos(screenlog, photodf)
    dur = datetime.now() - cp
    dur = dur.seconds + (dur.microseconds / 1000000)
    print('(Sort Photos took', round(dur, 2), 'seconds)\n\n')
    print('Sample_ID:\t\t\tNumber of photos:')
    for i, l in enumerate(photoslist):
        if len(l) > 0:
            print(screenlog.loc[i, 'Sample_ID'] + '\t\t\t' + str(len(l)))
    continue_prompt('Rename? [Y/N]')
    cp = datetime.now()
    rename(screenlog, photoslist)
    dur = datetime.now() - cp
    dur = dur.seconds + (dur.microseconds / 1000000)
    print('(Rename Photos took', round(dur, 2), 'seconds)\n\n')
    print('\nAlways remember to spot check renamed photos!')

main()



