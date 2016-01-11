import os
from bs4 import BeautifulSoup
import urllib
import zipfile
import string
from xml.etree import ElementTree
import json
import traceback
import re
# Converting PDF to TXT
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO


TERMS_PAGE = "http://ocw.mit.edu/terms"
BASE_PAGE = "http://ocw.mit.edu/courses/index.htm"
BASE_DIR = "Test"

def get_courses_set(base_page):
    htmltext = urllib.urlopen(base_page).read()
    soup = BeautifulSoup(htmltext, "html.parser")
    links = soup.findAll('a', {"rel":"coursePreview"})

    courses = []
    for link in links:
        courses.append("http://ocw.mit.edu" + link['href'])
    courses = set(courses)

    # first_course = list(courses)[:1]
    # return first_course

    return courses

def download_course(url, base_dir):
    url += "/download-course-materials"
    htmltext = urllib.urlopen(url).read()
    soup = BeautifulSoup(htmltext, "html.parser")
    downloadLink = "http://ocw.mit.edu" + soup.findAll('a', {"class":"downloadNowButton"})[0]['href']

    filename = downloadLink.split("/")[-1]

    fileplace = base_dir + "/" + filename.split(".")[0]
    if not os.path.isdir(fileplace):
        os.mkdir(fileplace)

    urllib.urlretrieve(downloadLink, fileplace + "/" + filename)

    return fileplace + "/" + filename

def findAllPDFs(filepath):
    zip = zipfile.ZipFile(filepath, 'r')
    # if zipfile.is_zipfile(filepath):
    #     zip = zipfile.ZipFile(filepath, 'r')
    # else:
    #     return
    list = zip.namelist()
    filelist = []
    for name in list:
        if name[-3:] == "pdf":
            # print name
            xmlname = name + ".xml"
            if xmlname in list:
                # print xmlname
                filelist.append(name)
                filelist.append(xmlname)

    return filelist

def convert_pdf_to_txt(path):

    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = file(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    fp.close()
    device.close()
    retstr.close()

    return text

def write_to_txt(text, path):
    name = path + ".txt"
    txtfile = open(name, "a")
    txtfile.write(text)
    txtfile.close()

def prepare_text(text):
    new_text = text

    # Cleaning from firs page
    pos = new_text.find("http://ocw.mit.edu/terms")
    if pos != -1 and pos < 200:
        new_text = new_text[pos + 26:]

    # Removing occurrences of "text box:"
    new_text = new_text.replace("text box:", "")

    return new_text.replace("\n", " ").replace("\t", " ").replace("\u", "")

def get_terms_information(terms_url):
    try:
        htmltext = urllib.urlopen(terms_url).read()
        soup = BeautifulSoup(htmltext, "html.parser")
        text = soup.findAll('div', {"id":"global_inner"})
        text = text[0].get_text(' ', strip=True)
        text = remore_whitespaces(text)
        text = remove_non_ascii(text)
        return text
    except:
        return ""

def get_couse_data_from_XML(xml_path):

    dom = ElementTree.parse(xml_path)
    namespaces = {'lom': 'http://ocw.mit.edu/xmlns/LOM'}

    title = dom.findall('lom:general/lom:title/lom:string', namespaces)[0].text

    abstract = dom.findall('lom:general/lom:description/lom:string', namespaces)[0].text.replace("\n", "")

    level = dom.findall('lom:educational/lom:context/lom:value', namespaces)[0].text

    instructors = []
    for c in dom.findall('lom:lifeCycle/lom:contribute', namespaces):
        instructors.append(c.findall('lom:entity', namespaces)[0].text)

    course_number = dom.findall('lom:general/lom:identifier/lom:entry', namespaces)[0].text

    return (title, abstract, level, instructors, course_number)

def get_lecture_data_from_XML(xml_path):
    dom = ElementTree.parse(xml_path)
    namespaces = {'lom': 'http://ocw.mit.edu/xmlns/LOM'}
    try:
        title = dom.findall('lom:general/lom:title/lom:string', namespaces)[0].text
        return title
    except:
        return False

def get_text_from_htm(htm_path):
    try:
        htmltext = open(htm_path, 'r').read()
        soup = BeautifulSoup(htmltext, "html.parser")
        text = soup.findAll('div', {"id":"course_inner_section"})
        text = text[0].get_text(' ', strip=True)
        return text
    except:
        return None

def html_readings(html_path):
    htmltext = open(html_path, 'r').read()
    soup = BeautifulSoup(htmltext, "html.parser")
    table = soup.findAll('div', {"class":"maintabletemplate"})
    readings = []
    try:
        rows = table[0].findAll("tbody")[0].findAll("tr")
        textfile = open(html_path[:-3] + "txt", "w")

        i = 0
        for row in rows:
            i += 1
            data = row.findAll("td")
            title = data[1].get_text(' ', strip=True)
            words = data[2].get_text(' ', strip=True)
            textfile.write(title)
            textfile.write(words)
            readings.append(
                {
                    "reading_" + str(i):{
                        "title" : title,
                        "words" : words
                    }
                }
            )
    except:
        words = table[0].get_text(' ', strip=True)
        readings.append(
            {
                "reading_" + str(i):{
                    "title" : "Readings",
                    "words" : words
                }
            }
        )

    return readings

def html_syllabus(html_path):
    htmltext = open(html_path, 'r').read()
    soup = BeautifulSoup(htmltext, "html.parser")
    data = soup.findAll('div', {"class":"course_inner_section"})

    syllabus = {
        "words" : data[0].get_text(' ', strip=True)
    }
    return syllabus

def add_object_to_json(z, path, jsondata, object_name):
    # Check if file exist coursename.zip/coursename/contents/assignments/index.htm
    namecourse = path.split("/")[-1]
    if namecourse + "/contents/" + object_name + "/index.htm" in z.namelist():
        # unpack file from ZIP
        z.extract(namecourse + "/contents/" + object_name + "/index.htm", BASE_DIR)
        text = get_text_from_htm(path + "/contents/" + object_name + "/index.htm")
        # if page is readable
        if text:
            text = remove_non_ascii(text)
            write_to_txt(text, path + "/contents/" + object_name + "/index")
            all_words = {
                "all_" + object_name: {
                    "words": text,
                    "original_filename": "index.htm",
                    "processed_filename": "index.txt"
                }
            }
            if object_name in jsondata["meta"]["open_courseware"].keys():
                jsondata["meta"]["open_courseware"][object_name].append(all_words)
            else:
                jsondata["meta"]["open_courseware"][object_name] = [all_words]
        else:
            os.remove(path + "/contents/" + object_name + "/index.htm")

def remove_non_ascii(text):
    return ''.join([i if 31 < ord(i) < 128 else ' ' for i in text])

def remore_whitespaces(text):
    return re.sub(' +', ' ', text).replace('\t', " ").replace("\n", " ")

def main_func():
    # Creating folder of project
    if not os.path.isdir(BASE_DIR):
        os.mkdir(BASE_DIR)

    # Finding all courses links
    print "Searching for all courses..."
    courses = get_courses_set(BASE_PAGE)
    print "Found " + str(len(courses)) + " courses"

    termtext = get_terms_information(TERMS_PAGE)

    # For each course ... do
    number = 0
    totalnumber = len(courses)
    for course in courses:
        try:
            number = number + 1
            print
            print "== " + str(number) + "/" + str(totalnumber) + " =="
            coursename = course.split("/")[-1]
            print "Course name : " + coursename

            # Getting download link of course
            # Returns name of ZIP file
            zip_path = download_course(course, BASE_DIR)
            path = ("/").join(zip_path.split("/")[:-1])
            print "Course has been downloaded to folder " + path

            # Searching all necessary files
            content = findAllPDFs(zip_path)
            print "Found " + str(len(content) / 2) + " text files"

            z = zipfile.ZipFile(zip_path, 'r')
            # Extracting all files
            for f in content:
                z.extract(f, BASE_DIR)

            # Extracting metadata: ./contents/index.htm.xml
            z.extract(path.split("/")[-1] + "/contents/index.htm.xml", BASE_DIR)
            (title, abstract, level, instructors, course_number) = get_couse_data_from_XML(path + "/contents/index.htm.xml")
            # Deleting meta-file
            os.remove(path + "/contents/index.htm.xml")


            jsondata = {
                "external_id"   :   coursename,
                "title"         :   title,
                # "date"          :   None,       # !!!!!!!!!!
                "abstract"      :   abstract,
                "url"           :   course,
                "meta"          :   {
                    "open_courseware": {
                        "class_info": {
                            "level"       : level,
                            "instructors" : instructors
                        },
                        "course_number"   : course_number,
                        "description"     : abstract
                    }
                }
            }


            # List of extracted from ZIP archive files
            contentlist = []
            for f in content:
                temp = BASE_DIR + "/" + f
                contentlist.append(temp)

            # For all PDF files do...
            print "Processing files..."
            num = 0
            n = 0
            for item in range(0, len(contentlist), 2):
                pdf_path = contentlist[item]
                xml_path = contentlist[item + 1]

                num += 1

                # Converting PDF to text
                text = convert_pdf_to_txt(pdf_path)

                # Deleting all non-ascii symbols
                text = prepare_text(text)
                text = remove_non_ascii(text)
                text = remore_whitespaces(text)

                # Creating TXT file for PDF
                pdf_name = string.join(pdf_path.split("/")[-1].split(".")[:-1])
                write_to_txt(text, ("/").join(pdf_path.split("/")[:-1]) + "/" + pdf_name)
                print "\t" + str(num) + ". File '" + pdf_name + ".txt' has been extracted"


                # Opening XML file and extracting additional information
                title = get_lecture_data_from_XML(xml_path)
                # Deleting XML file
                os.remove(xml_path)

                object_name = pdf_path.split("/")[-2]

                if object_name not in jsondata["meta"]["open_courseware"].keys():
                    jsondata["meta"]["open_courseware"][object_name] = []
                    n = 0
                n += 1

                jsondata["meta"]["open_courseware"][object_name].append(
                    {
                        object_name[:-1] + "_" + str(n) : {
                            "title" : title,
                            "original_filename": pdf_name + ".pdf",
                            "processed_filename": pdf_name + ".txt",
                            "words" : text
                        }
                    }
                )


            # Additionally looking for in ZIP

            # Assignments
            add_object_to_json(z, path, jsondata, "assignments")

            # Readings
            add_object_to_json(z, path, jsondata, "readings")

            # Syllabus
            add_object_to_json(z, path, jsondata, "syllabus")

            jsondata["terms"] = termtext

            # Composing all to JSON
            with open(path + "/" + path.split("/")[-1] + ".json", 'w') as outfile:
                json.dump(jsondata, outfile,  indent=4)

            # Deleting ZIP archive
            z.close()
            os.remove(zip_path)

            print "Course has been processed."

        except:
            print
            print
            print
            print "Something has gone wrong. Course with link " + str(course) + " hasn't been processed."
            traceback.print_exc()
            print
            print


if __name__ =="__main__":
    main_func()
