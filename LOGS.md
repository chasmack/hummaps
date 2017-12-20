
# Search Logs

### The Heartbreak of Search

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

The last search returns **177 maps** including [72RS131](README.md#individual-maps)
though it's not correct.

It runs as a [full township search](README.md#basic-search) of `t6n r1e `
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

### Type and Date

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

`type=pm date="2012 2015" `

Note the two parts of the date term are separated with a space so the
date term must be enclosed in double quotes.

---

### Trinity

```
108.206.239.152 30-Jan-2017 12:22:32 2rs175
108.206.239.152 30-Jan-2017 12:22:36 2ms175
108.206.239.152 30-Jan-2017 12:22:39 2maps175
108.206.239.152 30-Jan-2017 12:23:01 cant access trinity
```

No you can't access Trinity.

---

### Read the Docs

```
47.208.29.129 12-Aug-2017 12:59:00 s1 t3s r1w
47.208.29.129 12-Aug-2017 13:02:36 rm by: Drake
47.208.29.129 12-Aug-2017 13:02:51 RM by:Crivelli
47.208.29.129 12-Aug-2017 13:03:07 RM by:Drake
47.208.29.129 12-Aug-2017 13:03:25 RM by:Pacific Affiliates
47.208.29.129 12-Aug-2017 17:01:03 s1 t3s r1w
47.208.29.129 12-Aug-2017 17:01:20 RM
```

Try this:

`type:rm by:crivelli`

`type:rm by:drake`

`type:rm by:"pacific affiliates"`

The last search needs double quotes since there is a space 
in the [key name term](README.md#key-name-terms). 
That still won't turn up any maps though.
The `by:` key name is looking for a surveyor's name or LS/RCE number.

Also note that proper capitalization is not necessary. 
Letter case is NOT significant anywhere in the Hummaps search.

I look at these logs to see how people think the search *should* work.
The examples here almost meet the minimum threshold to make a change.
With only a small number of map types it would be pretty easy to have the
bare word search pick out map types.

Almost, but not quite. 

[***READ THE DOCS***](README.md)

---

### Latest Records

```
73.15.49.110 13-Sep-2017 14:07:11 tr651
73.15.49.110 13-Sep-2017 14:07:24 tr649
73.15.49.110 13-Sep-2017 14:07:39 tr650
73.15.49.110 13-Sep-2017 14:07:44 tr649
```

Poking around to find the newest tract map in the database?

The Hollins Index has a feature to show the newest maps for each map type in the database.
You can get the same information from Hummaps by restricting your search to a map type -

`type=rm`

`type=pm`

`type=rs`

Since the map list is ordered by date recorded the newest map will be first in the list.

---

### Maps Button

```
69.164.173.98 20-Oct-2017 07:58:13 s10 t5n r1w
69.164.173.98 20-Oct-2017 07:58:49 s10 t5n r1w
69.164.173.98 20-Oct-2017 07:59:22 s10 t5n r1w
69.164.173.98 20-Oct-2017 08:01:29 s10 t5n r1w
69.164.173.98 20-Oct-2017 08:03:38 s10 t5n r1w
69.164.173.98 20-Oct-2017 08:04:44 s10 t5n r1w
69.164.173.98 20-Oct-2017 08:07:03 s10 t5n r1w
```

I see a lot of this. I assume the user preforms a search, picks a map to display 
the map image, then hits the search button again to return to the *map list*. 
This works fine but you can also use the `maps` button in the top bar to return to the *map list*. 
And the `maps` button knows which map is being displayed 
and takes you back to that point in the list. The `Esc` key works the same way in *map view*. 

Check the [User Interface](README.md#user-interface) help page for all the details.

---

### Too Many Maps

```
73.15.49.110 27-Oct-2017 10:18:48 by=ohern
73.15.49.110 27-Oct-2017 10:18:55 by=o'hern
73.15.49.110 27-Oct-2017 10:19:07 by=hern
73.15.49.110 27-Oct-2017 10:19:16 by=ls4829
73.15.49.110 27-Oct-2017 10:19:32 by=4829
73.15.49.110 27-Oct-2017 10:35:33 by=4829 type=rs
73.15.49.110 27-Oct-2017 10:36:04 by=4829 type=rs date=2006
73.15.49.110 27-Oct-2017 10:36:10 by=4829 type=rs date=2007
73.15.49.110 27-Oct-2017 10:36:19 by=4829 type=rs date=2008
```

When a search turns up too many maps only the first 200 are displayed. This was
a cheap and easy way to prevent users from listing all 15,000 plus maps in the index.
If the maps you need are not being displayed you need to narrow your search.

This also shows some of the ways the `by=` [key name term](README.md#key-name-terms)
works (and doesn't work). The apostrophe in *O'Hern* should be optional but isn't. 

---

### Makes My Heart Soar

```
 75.109.248.173  20-Nov-2017 16:32:34     5K 200  query  13RS62
 75.109.248.173  20-Nov-2017 16:32:36   737K 200    map  013rs062-001.jpg
 75.109.248.173  20-Nov-2017 16:39:13    17K 200  query  by=herrick
 75.109.248.173  20-Nov-2017 16:39:31     2K 200  query  1901
 75.109.248.173  20-Nov-2017 16:39:42     3K 200  query  no 77
 75.109.248.173  20-Nov-2017 16:40:19     4K 200  query  s34 6n 2e
 75.109.248.173  20-Nov-2017 16:40:23   330K 200    map  001cr002-001.jpg
 75.109.248.173  20-Nov-2017 16:40:43   269K 200    map  001cr002-002.jpg
 75.109.248.173  20-Nov-2017 16:40:43   316K 200    map  002cr030-001.jpg
 75.109.248.173  20-Nov-2017 16:40:44   271K 200    map  002cr030-002.jpg
 75.109.248.173  20-Nov-2017 16:40:46   631K 200    map  061rs009-001.jpg
 75.109.248.173  20-Nov-2017 16:40:47   878K 200    map  061rs009-002.jpg
 75.109.248.173  20-Nov-2017 16:40:47   764K 200    map  038rs044-001.jpg
 75.109.248.173  20-Nov-2017 16:40:56     3K 200  query  s2 5n 2e
 75.109.248.173  20-Nov-2017 16:40:59   969K 200    map  058rs011-001.jpg
 75.109.248.173  20-Nov-2017 16:41:30   970K 200    pdf  058rs011.pdf
 75.109.248.173  20-Nov-2017 16:42:43   721K 200    map  039rs102-001.jpg
 75.109.248.173  20-Nov-2017 16:42:49   537K 200    map  031rs118-001.jpg
 75.109.248.173  20-Nov-2017 16:43:22   539K 200    pdf  031rs118.pdf
 75.109.248.173  20-Nov-2017 16:43:54     4K 200  query  s1 5n 2e
 75.109.248.173  20-Nov-2017 16:44:31  3458K 200    pdf  003rs037.pdf
 75.109.248.173  20-Nov-2017 16:46:02  1321K 200    pdf  005rs034.pdf
 75.109.248.173  20-Nov-2017 16:47:39     2K 200  query  16rs133
 75.109.248.173  20-Nov-2017 16:47:41   574K 200    map  016rs133-001.jpg
 75.109.248.173  20-Nov-2017 16:47:55     2K 200  query  16rs113
 75.109.248.173  20-Nov-2017 16:47:57   744K 200    map  016rs113-001.jpg
 75.109.248.173  20-Nov-2017 16:52:41     5K 200  query  13rs62
```

---

### AP Numbers

```

 108.209.219.59  12-Dec-2017 16:14:09     2K 200  query  221221008
 108.209.219.59  12-Dec-2017 16:14:45     2K 200  query  507091046
 108.209.219.59  12-Dec-2017 16:14:52     2K 200  query  507-091-046
 ```

No, at this point you can't search for AP numbers.

Mapping an AP number to a section search would be pretty straightforward 
and I will gladly add the feature if someone can supply me the data. 
You can make a project out of it. Use Tesseract OCR to parse the 
subdivisional information from the top of the AP map images.

`apn="507-091-046"`

Maybe someday.
