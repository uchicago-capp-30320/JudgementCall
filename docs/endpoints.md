# Endpoint Documentation # 


## Key Endpoints ##

### Landing - "/" ###

Parameters: None

Response: HTML page that shows dropdown, which upon completion generates 3 buttons.

Template Context Variables:

"button_name": """Start Exploring"""
"states": US_STATES
"state": state
"county": county

### Judges-St-County "judges/<str:state>/<str:county>/" ###

Parameters: state, county

Response: HTML page with list of collapsibles representing courts, containing
buttons to court-level analytics as well as previews of judges on judge cards.

Template Context Variables: 

"courts": courts
"fallback_url": fallback url to old judges view
"state": state
"county": county

### Court "judges/<str:court_id>/" ###

Parameters: court_id

Response: Judicial dashboard with judge cards, infographic, tenure and radar charts.

Template Context Variables:

"court": court
"court_id": court_id
"court_formatted": court_formatted
"details": details
gantt_data": court.gantt_json().text
"radar_data": []
"state": state
"county": county
"fallback_url": fallback url to judges_state_county

### Show_Person "people/<int:person_id>/" ###
Parameters: person_id

Response: Detailed profile of person with previous judicial experience.

Template Context Variables:

"person": person_info
"tenures": person_tenures
"topic_icons": get_topic_icons(person)
"opinions": person_opinions
"state": state
"county": county

### Elections-St-County "elections/<str:state>/<str:county>/" ###
Parameters: state, county

Response: HTML page with list of collapsibles representing courts, containing
buttons to court-level analytics as well as previews of candidates on judge cards.

Template Context Variables:
"person": person_info
"tenures": person_tenures
"topic_icons": get_topic_icons(person)
"opinions": person_opinions
"state": state
"county": county

### Analysis "analysis/" ###

Parameters: state, county

Response: HTML page with links to two high-level visualizations.

Template Context Variables:

"header": "Analysis"
"preamble": """Please explore our visualizations exploring high-level
judicial analytics."""
"states": US_STATES
"fallback_url": reverse("judgement_call:landing")
"state": state
"county": county



## Mostly Deprecated Endpoints ##
### Judges "judges/" ###
Parameters: request

Response: HTML page with state and county dropdown. Redirects upon submission,
skips if cached geodata available.

Template Context Variables:

"header": title
"preamble": blurb_about_page
"states": US_STATES
"button_name": "Find judges"
"fallback_url": reverse("judgement_call:landing")
"state": request.session.get("state")
"county": request.session.get("county")

### Elections "elections/" ###
Parameters: request

Response: HTML page with state and county dropdown. Redirects upon submission,
skips if cached geodata available.

Template Context Variables:

"header": "Elections"
"preamble": """Informed voting is important. Please select your state
and county to learn about any upcoming judicial elections."""
"button_name": "Find Elections"
"fallback_url": reverse("judgement_call:landing")
"state": state
"county": county

## Viz Related Endpoints ##
Parameters: state (optional)

Response: HTML page with SVG rendering of judicial tenure chart by state

Template Context Variables:

"gantt_data": json.text
"court_id": state
"court_name": court.name

## Predominantly Text Endpoints ##

### About "about/" ###

### 

## Other ##

### Get Counties "api/counties/<str:state>/" ###
Parameters: state

Response: API that returns available counties in that state to second dropdown.

Template Context Variables: N/A


    path(
        "judges/<str:state>/<str:county>/",
        views.judges_state_county,
        name="judges_state_county",
    ),
    path("people/<int:person_id>/", views.show_person, name="show_person"),
    path("methodology/", views.methodology, name="methodology"),
    path("about/", views.about, name="about"),
    path("elections/", views.elections, name="elections"),
    path(
        "elections/<str:state>/<str:county>/",
        views.elections_state_county,
        name="elections_state_county",
    ),
    path("analysis/", views.analysis, name="analysis"),
    path("analysis/polarization/", views.polarization, name="polarization"),
    path("analysis/spacejam/", views.spacejam, name="spacejam"),
    path("api/counties/<str:state>/", views.get_counties, name="get_counties"),
    path("gantt/", views.gantt, name="gantt"),
    path(
        "radar/<str:court_id>/<str2list:persons>/",
        views.get_individual_opinions_for_radar,
        name="radar",
    ),
    path("spacejam/", views.spacejam_backup, name="spacejam_backup"),
