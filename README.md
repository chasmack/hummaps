# Hummaps

Hummaps is an online version of the Humboldt County map index.
It is offered as an alternative to the MS Access based application
commonly referred to as the Hollins Index.

In February 2019 hosting and maintenance of Hummaps was transferred to 
the County of Humboldt. The County's version of Hummaps is currently hosted 
at [hummaps.com](https://hummaps.com). 

At this time I am unaware of any public hosting of the original Hummaps 
as described here.

We also have excerpts and commentary from the [User Search Logs.](LOGS.md)

### Basic search

Searches are text based. Type your search into the box at the top of the page.

A basic search looks like this: `s36 t2n r5e`

The township and range prefix is optional: `s36 2n 5e`

This should turn up the same maps as an equivalent search on Hollins.
Extra spaces around the search terms are ignored but you must
separate search terms by at least one space. Upper and lower case letters
can be used interchangeably.

To search in more than one section: `s36 t2n r5e + s35 t2n r5e`

Or more succinctly: `s35 s36 2n 5e`

To search an entire township: `2n 5e`

To search in more than one township: `s36 t2n r5e + s1 t1n r5e`

### Individual maps

To get individual maps: `27pm85 24rm59 21rs85 1ur438`

Parcel and tract maps can be referred to by their map number: `pm22 tr611`

Note there are no spaces separating the parts of an individual map name.

### Bare word search

A dubious feature is that any words not recognized as part of a
normal search term get thrown into a _bare word search_ of the FOR and DESCRIPTION fields.
This results in the ability to quickly search for any mention of a distinct word
or pattern of words as in `lanphere` or `mad river` but can also lead to unexpected results.
For instance, the search:

__WRONG:__ `t6n r4e s5`

is a full township search of `t6n r4e` qualified by the bare word `s5`.
This is not the same as doing a basic search of `s5 t6n r4e`.

### User Interface

The user interface has two main screens: the *map list* and the *map view*.

Search results are displayed in the map list. Maps with no map image 
are shown in gery. Selecting a map from the list opens the map view.

There are four buttons in the top bar -

* **maps** switches between the map list and the map view
* **next** moves to the next page or map
* **prev** moves to the previous page or map
* **about** links to the GitHub help page

In the map list -

* up and down arrows move through maps in the list
* tab and shift tab circulate through the user interface
* mouse click or enter select a map and open the map view

In the map view -

* \+ and - increase and decrease zoom
* mouse wheel increases and decreases zoom
* space bar zooms out to show the entire map
* dragging with the mouse button down pans
* right arrow displays the next page
* left arrow displays the previous page
* down arrow displays the next map
* up arrow displays the previous map
* escape returns to the map list

### Subsection search

A recent addition to the Hollins Index was the inclusion of subsection
information. Originally maps were indexed into sections adjacent
to the area being mapped thereby broadening searches. For example, 
if a map covered the sw/4 of section 1 it would also show up in searches 
of sections 2, 11 and 12. Subsections help limit the number of maps 
returned by a search.

To search for quarter sections: `sw/4 s15, nw/4 s22 t6n r5e`

Spanning a township line: `n/2 ne/4 s5 t6n r1e + s/2 se/4 S32 t7n r1e`

The smallest searchable subsection is 40 acres (quarter-quarter section). 

When a subsection is included in a search term the original Hollins
records for that section are not included in the results. One
strategy is to start with a narrow search and subsequently broaden
the search while excluding previous results.

The narrow search: `sw/4 s15, nw/4 s22 t6n r5e`

A broader search still using subsections: `1/1 s15, 1/1 s22 t6n r5e`

And finally the full search: `s15 s22 t6n r5e - 1/1 s15 1/1 s22 t6n r5e`

The term `1/1` does a subsection search for an entire section.
It is equalivent to searching both the `n/2` and `s/2` of a section.
The last search adds the original Hollins results but excludes
results from the previous searches. Commas are optional.

### Key name terms

Map type, surveyor, client, description and recording dates can
be included in a search using *key name terms*.

Key names are: `type:` `by:` `for:` `desc:` `date:`

Or without pressing shift: `type=` `by=` `for=` `desc=` `date=`

To search for parcel maps by a surveyor: `type:pm by:crivelli`

To add a date: `type:rs by:crivelli date:2015`

To add a range of dates: `type:rs by:crivelli date:"4/2012 2015"`

To add a description: `type:rs desc:"mad river"`

If the key name search term includes spaces it must be enclosed in
double quotes. Date terms can have one or two dates formatted as `mm/dd/yyyy`.
Dates with missing elements work as expected: `date:"4/2012 2015"`
is 4/1/2012 through 12/31/2015.

Searches are case-insensitive: `by:CrIveLLi type:Rm + by:cRIvELLi type:cR`

Key name search terms (except dates) are processed using regular
expressions. A little knowledge of regular expressions can be very
handy. A not-very-gentle explanation can be found at [postgresql.org](https://www.postgresql.org/docs/9.4/static/functions-matching.html#FUNCTIONS-POSIX-REGEXP).

Using regular expressions: `by:crivelli|pulley type:pm|rm`

An important use of regular expressions is in searching for descriptions.
Variations in spelling can often be smoothed over.

Using two search terms: `desc:patrick desc:point`

Using a regular expression: `desc:patrick.{1,3}point`

The regular expression searches for any description with the word
"patrick" followed by the word "point" with 1 to 3 characters between
the words. This smooths over the inconsistent use of an apostrophe
in the word patrick's. The first search using two terms will pick up
any descriptions having both "patrick" and "point" anywhere in the
description. 

Generally simple strings with alphanumeric characters and spaces
work as expected. However many punctuation characters take on
special meaning in a regular expression. Specifically, "." (dot),
"*" (asterisk), "+" (plus), "?" (question mark), "|" (vertical bar)
as well as certain less common combinations of other punctuation have
special meaning. Fortunately most of these special characters either do
not appear in the descriptions or are so common ("." and "+") that
including them in a search is not useful.

### Support

Please send your suggestions, comments and bug reports to Charlie.
