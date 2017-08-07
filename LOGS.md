
# Search Logs

#### The Heartbreak of Search

```
47.208.65.229 05-Jul-2017 15:44:41 72SUR131
47.208.65.229 05-Jul-2017 15:44:49 72
47.208.65.229 05-Jul-2017 15:45:02 72 SURVEYS
47.208.65.229 05-Jul-2017 15:45:06 72 SURVEY
47.208.65.229 05-Jul-2017 15:45:14 72 131
47.208.65.229 05-Jul-2017 15:45:18 131
47.208.65.229 05-Jul-2017 15:45:51 1 MAPS 1
47.208.65.229 05-Jul-2017 15:46:24 BOOK 72 SURVEYS PAGE 131
47.208.65.229 05-Jul-2017 15:46:32 BOOK 72 SURVEYS PAGE 1
47.208.65.229 05-Jul-2017 15:46:43 777777
47.208.65.229 05-Jul-2017 15:46:46 7
47.208.65.229 05-Jul-2017 15:47:55 32 T6N R1E
```

The last search returns **177 maps** though it's not correct.
It's run as a [full township search](README.md#basic-search) of `t6n r1e `
qualified by the [bare word](README.md#bare-word-search) `32 `.

This is not the same as a [basic search](README.md#basic-search)
for maps in section 32:

`s32 6n 1e `

To see the difference run two searches:

`s32 6n 1e - 32 6n 1e `

`32 6n 1e - s32 6n 1e `

The first returns **32 maps** in the basic section search but missing 
from the bare word search. The second returns **82 maps**
in the bare word search but not returned in the section search.

Little details make all the difference.

---

#### Date and Type

```
216.102.9.150 03-Aug-2017 13:17:52 pm 2012-2015
216.102.9.150 03-Aug-2017 13:18:05 pm: 2012-2015
```

This is complicated both in what the user is trying to do and what is actually happening.

It's assumed the user wants all parcel maps for the years 2012 to 2015.

The first search turns up one map - PM2012. Though it's not 
what was intended this appears to work but for all the wrong reasons.
What actually happens is the search is broken into two
[bare word searches](README.md#bare-word-search): `pm 2012 ` and `2015 `.
The first finds PM2012 since that text appears in the map description.
The second removes any results containing the text 2015. To see why this
is wrong compare the results for `PM20 ` and `PM 20 `.

The second search throws a colon into the first bare word term: **No maps**

What's needed are two [key name terms](README.md#key-name-terms):

`date="2012 2015" type=pm `

Note the two parts of the date term are separated with a space so the
date term must be enclosed in double quotes.

---
