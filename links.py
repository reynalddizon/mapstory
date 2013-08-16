links = {
    "wiki" : {
        "prefix" : "http://wiki.mapstory.org/index.php?title=",
        "links" : [
            ("curation_guide_ratings", "Curation_Guide#Ratings")
        ]
    }
}

for cat in links.values():
    link_list = cat['links']
    lookup = {}
    prefix = cat.get('prefix','')
    for link in link_list:
        lookup[link[0]] = prefix + link[1]
    cat['links'] = lookup

def resolve_link(cat, name):
    cat = links[cat]
    return cat['links'][name]
