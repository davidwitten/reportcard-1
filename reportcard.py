# Report Card

# Import
import re
import getpass
import requests
import bs4

# Constant
MAIN_URL = "https://www.edline.net"
LOGIN_URL = MAIN_URL + "/InterstitialLogin.page"
LOGIN_POST_URL = MAIN_URL + "/post/InterstitialLogin.page"
HOME_POST_URL = MAIN_URL + "/post/GroupHome.page"
NOTIFICATIONS_URL = MAIN_URL + "/Notifications.page"
DOCLIST_URL = MAIN_URL + "/UserDocList.page"

REPORTS_URL = "/Current_Assignments_Report"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/31.0.1650.63 "
                  "Safari/537.36 "
}

LOGIN_DATA = {
    "TCNK": "authenticationEntryComponent",
    "submitEvent": "1",
    "guestLoginEvent": "",
    "enterClicked": "true",
    "bscf": "",
    "bscv": "",
    "targetEntid": "",
    "ajaxSupported": "yes"
}

DOCLIST_DATA = {
    "invokeEvent": "viewUserDocList",
}

# Containers
class Course:
    """Container class that keeps track of name, date updated, and link."""

    def __init__(self, name, date, link):
        """Initialize a new course."""
        self.name = name
        self.date = date
        self.link = link
        self.grades = {}

    def __repr__(self):
        """Magic method for representing a course."""
        return "Course: %s" % self.name

# Functions
def _login(username, password, verbose=False):
    """Log into Edline using the provided credentials and return the session
    location and cookies."""
    
    response = requests.get(LOGIN_URL, headers=HEADERS)
    if response.status_code != 200:
        print("Failed to access Edline!", file=sys.stderr)
        return
    cookies = response.cookies

    credentials = LOGIN_DATA.copy()
    credentials.update({"screenName": username, "kclq": password})
    response = requests.post(LOGIN_POST_URL, credentials, headers=HEADERS,
                             cookies=cookies, allow_redirects=False)
    if response.headers["location"] == NOTIFICATIONS_URL:
        print("Bad login credentials!", file=sys.stderr)
        return
    cookies.update(response.cookies)
    if verbose: print("Logged into %s" % response.headers["location"])
    
    return response.headers["location"], cookies
    
def _courses(username, password, verbose=False):
    """Get the currently listed courses on Edline for the user with the
    provided credentials. Determines which classes to select from the private
    reports page by checking if they are described as a current assignments
    report."""

    location, cookies = _login(username, password)
    response = requests.post(HOME_POST_URL, DOCLIST_DATA, headers=HEADERS,
                             cookies=cookies)
    cookies.update(response.cookies)
    response = requests.get(DOCLIST_URL, headers=HEADERS, cookies=cookies)
    soup = bs4.BeautifulSoup(response.text)

    courses = []
    for report in soup.findChildren("tr")[4:-2]:
        raw = map(lambda s: s.strip(), report.get_text().split("\n"))
        date, view, name, description = filter(None, raw)
        link = report.findChild("a", {"class": "lochomepage"}).attrs["href"]

        if description == "Current Assignments Report":
            courses.append(Course(name, date, link))
    if verbose: print("Scraped information from reports")

    return location, cookies, courses

def _quarters(username, password, verbose=False):
    """Get listed quarters from the private reports. No implementation yet."""

    location, cookies = _login(username, password)
    response = requests.post(HOME_POST_URL, DOCLIST_DATA, headers=HEADERS,
                             cookies=cookies)
    cookies.update(response.cookies)
    response = requests.get(DOCLIST_URL, headers=HEADERS, cookies=cookies)
    soup = bs4.BeautifulSoup(response.text)

    quarters = set()
    for report in soup.findChildren("tr")[4:-2]:
        raw = map(lambda s: s.strip(), report.get_text().split("\n"))
        date, view, name, description = filter(None, raw)
        link = report.findChild("a", {"class": "lochomepage"}).attrs["href"]

        if re.match(r"Marking Period \d as of .+", description):
            quarters.add("/" + description[:-4].replace(" ", "_"))
    if verbose: print("Scraped quarters from reports")

    return location, cookies, list(quarters)

def _grades(username, password, verbose=False):
    """Get the currently listed courses on Edline as well as the grades entered
    in the current assignments report."""

    location, cookies, courses = _courses(username, password)
    for course in courses:
        link = MAIN_URL + course.link + REPORTS_URL
        response = requests.get(link, headers=HEADERS, cookies=cookies)
        soup = bs4.BeautifulSoup(response.text)
        source = soup.findChild("iframe", {"id": "docViewBodyFrame"})["src"]
        response = requests.get(source, headers=HEADERS, cookies=cookies)

        soup = bs4.BeautifulSoup(response.text)
        raw = []
        for child in soup.findChildren("td", {"valign": "center"}):
            text = child.get_text()       
            if text == "Current Assignments": break
            if text != "\xa0" and text:
                raw.append(text)

        course.grades["cumulative"] = {"percentage": raw[-2], "letter": raw[-1]}
        raw = raw[:-3]

        for i in range(len(raw) // 4):
            category, weight, fraction, percentage = raw[i:i+4]
            course.grades[category] = {"weight": weight, "fraction": fraction,
                                       "percentage": percentage}
    if verbose: print("Scraped grades from reports")
        
    return location, cookies, courses

def _interactive():
    """Run the interactive shell reportcard."""
    overview_template = "%-32s %-7s %-5s %s"
    
    username = input("Username: ")
    password = input("Password: ")    

    location, cookies, courses = _grades(username, password)
    grade = 0
    print()
    for course in courses:
        grade += 'EDCBA'.index(course.grades["cumulative"]["letter"])
    for course in courses:
        print(overview_template % (course.name,
                                   course.grades["cumulative"]["percentage"],
                                   course.grades["cumulative"]["letter"],
                                   course.date))
    print(grade/len(courses))
_interactive()
