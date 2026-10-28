# Golden set review

For each question: is it clear, is the expected answer right, and do the listed
sources really support it? Reply with the IDs to drop or fix (and why).

**Flags from my own pass (please confirm or overrule):**
- **G04:** HotpotQA's answer "NCAA" does not answer "what athletic *conference*". Drop, or fix the answer from the paragraph.
- **G40:** expected "French composer" → should be just "French".
- **G44 / G45:** both about *The Yellow Wallpaper* / Charlotte Perkins Gilman, so they're nearly the same fact. Consider dropping one.
- **G12, G18:** expected answers are full names ("Charlotte Lucy Gainsbourg", "Phillip John Mogg"). Fine, but the scorer will also accept the short name via token F1.
- **G03:** "grewwacke" is a typo in the original HotpotQA question. I left it on purpose (realistic input).
- **Unanswerable G19–G22:** made by deleting the only paragraph in the corpus that states the answer. Check that the question isn't answerable from the remaining paragraph on common sense alone.

## G01 · bridge

**Q:** The Ghost and Mrs. Muir was a film that was created by the studios located in what area of Los Angeles?

**Expected:** Century City — status `answered`

> **The Ghost and Mrs. Muir** — The Ghost and Mrs. Muir (1947) is a romantic-fantasy film starring Gene Tierney and Rex Harrison. It was directed by Joseph L. Mankiewicz, and is based on a 1945 novel written by Josephine Leslie under the pseudonym of R. A. Dick. In 1945, 20th Century Fox bought the film rights to the novel, which had been published only in the United Kingdom at that time. It was shot entirely in California.

> **20th Century Fox** — Twentieth Century Fox Film Corporation (known as Twentieth Century-Fox Film Corporation with hyphen from 1935 until 1985, stylized as 20th Century Fox or simply known as Fox or 20th Century Fox Pictures) is an American film studio currently owned by 21st Century Fox. It is one of the "Big Six" major American film studios and is located in the Century City area of Los Angeles, just west of Beverly Hills. The studio was owned by News Corporation from 1984 to 2013.

- [ ] OK

## G02 · bridge

**Q:** What was the duck character's name in the Disney cartoon with the music that sounded like The Mexican Hat Dance?

**Expected:** Donna — status `answered`

> **Don Donald** — Don Donald is a 1937 American animated short film produced by Walt Disney Productions and released by United Artists. The cartoon follows Donald Duck attempting to woo a female Mexican duck named Donna. It was directed by Ben Sharpsteen and features music by Paul J. Smith which was adapted from the Mexican folk songs "Cielito Lindo" and "Jarabe Tapatío." Clarence Nash voiced both Donald and Donna.

> **Jarabe Tapatío** — The "Jarabe Tapatío", better known internationally as "The Mexican Hat Dance", is a popular Mexican dance also popular in other countries such as Cuba, Peru, and the Dominican Republic, that has come to symbolize Latin America both domestically and internationally.

- [ ] OK

## G03 · bridge

**Q:** A 202 pound slab of grewwacke covered in runes on its face and side indicated the Scandinavians came to Minnesota in what century?

**Expected:** 14th century — status `answered`

> **Kensington, Minnesota** — Kensington is a city in Douglas County, Minnesota, United States. The population was 292 at the 2010 census. The city is notable in Minnesota history for being the place where the famous, if questionable, Kensington Runestone was first displayed. The stone tablet may indicate that Scandinavians had come to Minnesota in the 14th century. It is now at a museum in nearby Alexandria, Minnesota.

> **Kensington Runestone** — The Kensington Runestone is a 202 lb slab of greywacke covered in runes on its face and side.

- [ ] OK

## G04 · bridge

**Q:** What athletic conference are Valdosta State Blazers football part of?

**Expected:** NCAA — status `answered`

> **Valdosta State Blazers football** — The Valdosta State football team represents Valdosta State University in football. The Blazers are a member of the Gulf South Conference (GSC) in NCAA Division II. Valdosta State University has had a football team since 1981. The Blazers play in Bazemore–Hyder Stadium in Valdosta, Georgia, which has a capacity of 11,249. The Stadium is also the home of the historical Valdosta High School Wildcats, known as "the winningest high school football team in the country". The Blazers have won a total of three Division II National Championship titles (2004, 2007 and 2012).

> **Gulf South Conference** — The Gulf South Conference (GSC) is a collegiate athletic conference affiliated at the National Collegiate Athletic Association (NCAA) Division II level which operates in the southeastern United States.

- [ ] OK

## G05 · bridge

**Q:** What Russian composer was notably conducted by Konstantin Saradzhev and received a lifetime pension in 1884?

**Expected:** Pyotr Ilyich Tchaikovsky — status `answered`

> **Konstantin Saradzhev** — Konstantin Saradzhev (also "Constantin Saradgeff", born Saradzhian; 8 October 1877 – 22 July 1954) was an Armenian conductor and violinist. He was an advocate of new Russian music, and conducted a number of premieres of works by Pyotr Ilyich Tchaikovsky, Modest Mussorgsky, Igor Stravinsky, Sergei Prokofiev, Nikolai Myaskovsky, Dmitri Shostakovich, and Aram Khachaturian. His son Konstantin Konstantinovich Saradzhev was a noted bell ringer and musical theorist.

> **Pyotr Ilyich Tchaikovsky** — Pyotr Ilyich Tchaikovsky ( ; Russian: Пётр Ильи́ч Чайко́вский ; 25 April/7 May 1840 – 25 October/6 November 1893), often anglicized as Peter Ilich Tchaikovsky, was a Russian composer of the romantic period, some of whose works are among the most popular music in the classical repertoire. He was the first Russian composer whose music made a lasting impression internationally, bolstered by his appearances as a guest conductor in Europe and the United States. Tchaikovsky was honored in 1884, by Emperor Alexander III, and awarded a lifetime pension.

- [ ] OK

## G06 · bridge

**Q:** What constituency in North East Lincolnshire was mayored by Richard Barber in 1388?

**Expected:** Great Grimsby — status `answered`

> **Richard Barber (MP)** — Richard Barber was the member of Parliament for Great Grimsby in 1388 and mayor of that town.

> **Great Grimsby (UK Parliament constituency)** — Great Grimsby is a constituency in North East Lincolnshire represented in the House of Commons of the Parliament of the United Kingdom since May 2015 by Melanie Onn of the Labour Party.

- [ ] OK

## G07 · bridge

**Q:** the Buddha Bar became known internationally for issuing popular compilations of a subgenre of electronic music whose name is dreived from a slang word for what?

**Expected:** relax — status `answered`

> **Buddha Bar compilation albums** — The Buddha Bar compilation albums are a widely acclaimed series of compilation albums issued by the Buddha Bar bar, restaurant, and hotel franchise created by restaurateur Raymond Visan and DJ and interior designer Claude Challe in Paris, France. Following its establishment, the Buddha Bar "became a reference among foreign yuppies and wealthy tourists visiting the city", and "has spawned numerous imitators", becoming popular in part because of the DJ's choice of eclectic, avant-garde music. It became known internationally for issuing popular compilations of lounge, chill-out music and world music, also under the Buddha Bar brand, released by George V Records. Buddha Bar began issuing compilations in 1999, and has since "made a name for itself with its Zen lounge music CDs and remains a hit – especially with tourists".

> **Chill-out music** — Chill-out music (sometimes also chillout, chill out or simply chill) is a subgenre of electronic music and an umbrella term for several styles of electronic music characterized by their mellow style and mid-tempo beats, "chill" being derived from a slang word for "relax".

- [ ] OK

## G08 · bridge

**Q:** What did an Indian woman do,who came to international attention, that had a 2006 British biographical drama film, directed by Jag Mundhra made about her?

**Expected:** killed her abusive husband — status `answered`

> **Provoked (film)** — Provoked is a 2006 British biographical drama film, directed by Jag Mundhra. It stars Aishwarya Rai, Naveen Andrews, Miranda Richardson, Robbie Coltrane, Nandita Das and Steve McFadden. The film is loosely based on the true story of Kiranjit Ahluwalia, who killed her abusive husband.

> **Kiranjit Ahluwalia** — Kiranjit Ahluwalia (born 1955) is an Indian woman who came to international attention after burning her husband to death in 1989 in the UK. She claimed it was in response to ten years of physical, psychological, and sexual abuse. After initially being convicted of murder and sentenced to life in prison, Ahluwalia's conviction was later overturned on grounds of inadequate counsel and replaced with voluntary manslaughter. Although her submission of provocation failed (under "R v Duffy" the loss of control needed to be sudden, which this was not), she successfully pleaded the partial defence of diminished responsibility under s.2 Homicide Act 1957 on the grounds that fresh medical evidence (which was not available at her original trial) may indicate diminished mental responsibility.

- [ ] OK

## G09 · bridge

**Q:** Which city is the metropolitan area that contains the Independent School League centered on?

**Expected:** Washington, D.C. — status `answered`

> **Independent School League (Washington, D.C. area)** — The Independent School League or ISL is a group of seventeen preparatory schools located in the Washington metropolitan area of the United States that compete with each other athletically. All competitors in the ISL are girls, but not all schools are "all-girls" schools. The league is broken into two divisions: A and AA. The schools which compete in each division vary by sport.

> **Washington metropolitan area** — The Washington metropolitan area is the metropolitan area centered on Washington, D.C., the capital of the United States. The area includes all of the federal district and parts of the U.S. states of Maryland and Virginia, along with a small portion of West Virginia.

- [ ] OK

## G10 · bridge

**Q:** Which of the rapper born on June 19, 1983 has Hollis on his track? 

**Expected:** Macklemore — status `answered`

> **Hollis (singer)** — Hollis Wong-Wear, known mononymously as Hollis, is an American singer-songwriter and creative producer. She is best known for featuring on "White Walls", a song by Macklemore and Ryan Lewis, which also featured Schoolboy Q. Hollis is also a spoken-word artist. Her major debut was on Macklemore & Ryan Lewis' debut album, "The Heist". This was followed by the single "White Walls" in which she did the vocals for Macklemore and Ryan Lewis. This song peaked at number 15 on the Billboard Hot 100 chart.

> **Macklemore** — Benjamin Hammond Haggerty (born June 19, 1983), known by his stage name Macklemore ( ), and formerly Professor Mack Lemore, is an American rapper from Seattle, Washington. He has collaborated with producer Ryan Lewis as Macklemore & Ryan Lewis. Since 2000, he has independently released one mixtape, three EPs, and four albums.

- [ ] OK

## G11 · comparison

**Q:** Are both Naser Mestarihi and Lovefoxxx a singer?

**Expected:** yes — status `answered`

> **Naser Mestarihi** — Naser Mestarihi (Arabic: ناصر شاهر صالح المستريحي; born 14 October 1987) is a Qatari born Jordanian-Pakistani singer-songwriter and multi-instrumentalist (guitars, bass & vocals) who is based out of Doha, Qatar and Dubai, United Arab Emirates. Naser is the first rock musician to ever officially release a rock album out of Qatar, the "Naser Mestarihi EP". He released his second album "1987" on 17 June 2013.

> **Lovefoxxx** — Luísa Hanae Matsushita (born February 25, 1984), known by her stage name Lovefoxxx, is the lead singer of the Brazilian indie band Cansei de Ser Sexy (CSS).

- [ ] OK

## G12 · comparison

**Q:** Who started earlier, Ghinzu or Charlotte Gainsbourg?

**Expected:** Charlotte Lucy Gainsbourg — status `answered`

> **Ghinzu** — Ghinzu is an alternative rock band founded in 1999 in Brussels, Belgium.

> **Charlotte Gainsbourg** — Charlotte Lucy Gainsbourg (born 21 July 1971) is a British-French actress and singer. She is the daughter of English actress Jane Birkin and French singer and songwriter Serge Gainsbourg. After making her musical debut with her father on the song "Lemon Incest" at the age of 12, she released an album with her father at the age of 15. More than 20 years passed before she released three albums as an adult ("", "IRM" and "Stage Whisper") to commercial and critical success. Gainsbourg has also appeared in many films, including several directed by Lars von Trier, and has received both a César Award and the Cannes Film Festival Best Actress Award.

- [ ] OK

## G13 · comparison

**Q:** Which film is more recent, No End in Sight, or Station to Station?

**Expected:** Station to Station — status `answered`

> **No End in Sight** — No End in Sight is a 2007 documentary film about the American occupation of Iraq. The film marks the directorial debut of Academy Award-winning documentary film producer Charles H. Ferguson. The film premiered January 22, 2007 at the 2007 Sundance Film Festival. The film opened in limited release in the United States on July 27, 2007, playing in two theaters. s of 2007 , the film had grossed $1.4 million, and had been released on DVD.

> **Station to Station (film)** — Station to Station is the 2014 film of Doug Aitken's 2013 "Nomadic Happening", the film is made up of 62 one-minute films. It was distributed internationally in 2015 following its release at the Sundance Film Festival.

- [ ] OK

## G14 · comparison

**Q:** Who was born first, Daphne du Maurier or Pietro di Donato?

**Expected:** Daphne du Maurier — status `answered`

> **Daphne du Maurier** — Dame Daphne du Maurier, Lady Browning, DBE ( ; 13 May 1907 – 19 April 1989) was an English author and playwright.

> **Pietro di Donato** — Pietro Di Donato (April 3, 1911–January 19, 1992) was an American writer and bricklayer best known for his novel, "Christ in Concrete", which recounts the life and times of his bricklayer father, Geremia, who was killed in 1923 in a building collapse. The book, which portrayed the world of New York's Italian-American construction workers during The Great Depression, was hailed by critics in the United States and abroad as a metaphor for the immigrant experience in America, and cast di Donato as one of the most celebrated Italian American novelists of the mid-20th century.

- [ ] OK

## G15 · comparison

**Q:** Who worked on most different areas, Ali Campbell or Mr Lordi?

**Expected:** Mr Lordi — status `answered`

> **Ali Campbell** — Alistair Ian "Ali" Campbell (born 15 February 1959) is an English singer and songwriter who was the lead singer and a founding member of the English reggae band UB40. As part of UB40, Campbell sold over 70 million records worldwide and toured the globe for 30 years. In 2008, Campbell left UB40 and embarked on a solo career. In 2012, Campbell was announced as one of the three judges on the judging panel of the TV show, "New Zealand's Got Talent". In August 2014, Campbell announced that he had reunited with former UB40 band mates Astro and Mikey to record a new album, "Silhouette", released on 6 October 2014.

> **Mr Lordi** — Tomi Petteri Putaansuu (born 15 February 1974) is a Finnish musician, businessman, special effect make-up artist, songwriter, actor, painter, comics artist and graphic designer. He is best known by his stage name Mr Lordi a.k.a. Mr L.

- [ ] OK

## G16 · comparison

**Q:** Are both Jack Russell Terrier and Bullmastiff types of dogs?

**Expected:** yes — status `answered`

> **Jack Russell Terrier** — The Jack Russell Terrier is a small terrier that has its origins in fox hunting. It is principally white-bodied and smooth, rough or broken-coated but can be any colour.

> **Bullmastiff** — The Bullmastiff is a large-sized breed of domestic dog, with a solid build and a short muzzle. The Bullmastiff shares the characteristics of molosser dogs, and was originally developed by 19th-century gamekeepers to guard estates. The breed's bloodlines are drawn from the English Mastiff and the extinct Old English Bulldog. It was recognized as a purebred dog by the English Kennel Club in 1924. They are quiet dogs and very rarely bark.

- [ ] OK

## G17 · comparison

**Q:** Are both Elinor Lipman and Ernst Toller German?

**Expected:** no — status `answered`

> **Elinor Lipman** — Elinor Lipman (born October 16, 1950) is an American novelist, short story writer, and essayist.

> **Ernst Toller** — Ernst Toller (1 December 1893 – 22 May 1939) was a German left-wing playwright, best known for his Expressionist plays. He served in 1919 for six days as President of the short-lived Bavarian Soviet Republic, and was imprisoned for five years for his actions. He wrote several plays and poetry during that period, which gained him international renown. They were performed in London and New York as well as Berlin. In 2000, several of his plays were published in an English translation.

- [ ] OK

## G18 · comparison

**Q:** Which singer was born first Phil Mogg or Lynn Strait?

**Expected:** Phillip John Mogg — status `answered`

> **Phil Mogg** — Phillip John Mogg (born 15 April 1948, Wood Green, North London) is the lead singer for the English rock band UFO, which he formed with longtime friends Pete Way and Andy Parker. Mogg wrote the majority of the band's lyrics, with the music being written by Way, Michael Schenker, and later, Paul Raymond, but Schenker left to launch his solo career in 1979. Beginning in 1997, Mogg and Way, under the moniker Mogg/Way, released a couple of albums- "Edge of the World" and "Chocolate Box". With UFO on hiatus, Phil formed another side project, $ign of 4. In late 2003, having regained the rights to the UFO name from Schenker, Mogg spoke with Pete Way and Paul Raymond, and ended up having a reunion tour which later brought the band back for good, with newly hired American guitarist Vinnie Moore. The band then released several new albums : "Showtime", "You Are Here", "The Monkey Puzzle", "The Visitor", "Seven Deadly" and "A Conspiracy of Stars".

> **Lynn Strait** — James Lynn Strait (August 7, 1968 – December 11, 1998) was the lead singer and lyricist for the rock band Snot. He died in a car accident on December 11, 1998 at the age of 30.

- [ ] OK

## G19 · unanswerable

**Q:** Who is the current president of the governing body which organizes the Asian Martial Arts Games?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

**Deleted paragraph** (held the answer 'Sheikh Fahad Al-Sabah'): *Olympic Council of Asia* — The Olympic Council of Asia (OCA) is a governing body of sports in Asia, currently with 45 member National Olympic Committee. The current president is Sheikh Fahad Al-Sabah. The oldest NOCs are from Japan and the Philippines, recognized by the International Olympic Committee (IOC) in 1911; whereas East Timor is the newest, joining in 2003. The headquarters of OCA are located at Kuwait City.

*The only paragraph stating the answer is deleted from the golden index.*

- [ ] OK

## G20 · unanswerable

**Q:** What were this group of people referred to as ("Not Ready For what?) that Jon Lovitz was a member of from 1985 to 1990?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

**Deleted paragraph** (held the answer 'Prime Time Players'): *Saturday Night Live cast members* — The following is a list of "Saturday Night Live" cast members, past and present. The cast members of "Saturday Night Live" were originally referred to as the "Not Ready For Prime Time Players."

*The only paragraph stating the answer is deleted from the golden index.*

- [ ] OK

## G21 · unanswerable

**Q:** Who are the parents of the goddess the title of the final novel of the "Percy Jackson & the Olympians" series refers to?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

**Deleted paragraph** (held the answer 'Cronus and Rhea'): *Hestia* — In Ancient Greek religion, Hestia ( ; Greek: Ἑστία , "hearth" or "fireside") is a virgin goddess of the hearth, architecture, and the right ordering of domesticity, the family, the home, and the state. In Greek mythology, she is a daughter of Cronus and Rhea.

*The only paragraph stating the answer is deleted from the golden index.*

- [ ] OK

## G22 · unanswerable

**Q:** When was the arena which hosted the Call of Duty: Experience 2016 opened ?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

**Deleted paragraph** (held the answer 'December 30, 1967,'): *The Forum (Inglewood, California)* — The Forum is a multi-purpose indoor arena in Inglewood, California, adjacent to Los Angeles. Located between West Manchester Boulevard, across Pincay Drive and Kareem Court, it is north of the under-construction Los Angeles Stadium at Hollywood Park and the new Hollywood Park Casino. It is about three miles east of Los Angeles International Airport. Opening on December 30, 1967, the Forum was an unusual and groundbreaking structure. Architect Charles Luckman's vision was brought to life by engineers Carl Johnson and Svend Nielsen, who were able to engineer the structure so that it had no major support pillars. This had previously been unheard of in an indoor arena the size of the Forum.

*The only paragraph stating the answer is deleted from the golden index.*

- [ ] OK

## G23 · unanswerable

**Q:** Who won the 2030 FIFA World Cup?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

*Not in the corpus (checked by phrase search).*

- [ ] OK

## G24 · unanswerable

**Q:** What was Upgaming's total revenue in 2025?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

*Not in the corpus (checked by phrase search).*

- [ ] OK

## G25 · unanswerable

**Q:** How many people lived in the Ares Base colony on Mars in 2040?

**Expected:** (no answer: should refuse) — status `insufficient_evidence`

*Not in the corpus (checked by phrase search).*

- [ ] OK

## G26 · contradictory

**Q:** Shinola, Vol. 1, is a compilation album by the band Ween, an American alternative rock band formed in New Hope, Pennsylvania, in which year?

**Expected:** 1984 — status `contradictory`
**Conflicting value in the new document:** 1991

> **Ween** — Ween is an American alternative rock band formed in New Hope, Pennsylvania, in 1984 by childhood friends Aaron Freeman and Mickey Melchiondo, better known by their respective stage names, Gene Ween and Dean Ween. After meeting in a middle-school typing class, the two began playing music and immediately chose the name Ween as well as their Ramones-inspired pseudonyms. Ween performed as a duo backed by a Digital Audio Tape for the band's first ten years of existence before expanding to a four- (and later five-) piece act. The band's highest charting single is "Push th' Little Daisies", which was a hit in the United States and Australia.

**Synthetic upload:** `docs/G26_archive_ween.pdf`

- [ ] OK

## G27 · contradictory

**Q:** David Bain Oliver was a teacher of flute at a conservatoire formed in what year?

**Expected:** 2005 — status `contradictory`
**Conflicting value in the new document:** 2012

> **Trinity Laban Conservatoire of Music and Dance** — Trinity Laban Conservatoire of Music and Dance is a music and dance conservatoire based in London, England. It was formed in 2005 as a merger of two older institutions – Trinity College of Music and Laban Dance Centre. Today the conservatoire has 985 undergraduate and postgraduate students based at three campuses in Greenwich (Trinity), Deptford/New Cross (Laban) and New Cross (Laurie Grove) in London.

**Synthetic upload:** `docs/G27_archive_trinity_laban_conservatoire_of_music_and.docx`

- [ ] OK

## G28 · contradictory

**Q:** Paul McEuen received his B.S. in engineering physics at a university offering how many master's programs?

**Expected:** 160 — status `contradictory`
**Conflicting value in the new document:** 323

> **University of Oklahoma** — The University of Oklahoma (OU) is a coeducational public research university in Norman, Oklahoma. Founded in 1890, it had existed in Oklahoma Territory near Indian Territory for 17 years before the two became the state of Oklahoma. In Fall 2016 the university had 31,250 students enrolled, most at its main campus in Norman. Employing nearly 3,000 faculty members, the school offers 152 baccalaureate programs, 160 master's programs, 75 doctorate programs, and 20 majors at the first professional level. David Lyle Boren, a former U.S. Senator and Oklahoma Governor, has served as the university's president since 1994.

**Synthetic upload:** `docs/G28_archive_university_of_oklahoma.md`

- [ ] OK

## G29 · contradictory

**Q:**  Kevin Olekaibe played college basketball for an institution on a campus that covers how many acres?

**Expected:** 332 — status `contradictory`
**Conflicting value in the new document:** 667

> **University of Nevada, Las Vegas** — The University of Nevada, Las Vegas (UNLV) is an American public research university in the Las Vegas suburb of Paradise, Nevada. The 332 acre campus is about 1.6 mi east of the Las Vegas Strip. The university includes the Shadow Lane Campus, just east of the University Medical Center of Southern Nevada, which houses the School of Dental Medicine— the only dental school in Nevada. In addition, UNLV's law school, the William S. Boyd School of Law, is also the only law school in the state.

**Synthetic upload:** `docs/G29_archive_university_of_nevada_las_vegas.pdf`

- [ ] OK

## G30 · contradictory

**Q:** In which year did this journalist and former Australian politician featured in the Australian television program "The Cabinet" alongside Craig Emerson resign from parliament?

**Expected:** 2012 — status `contradictory`
**Conflicting value in the new document:** 2019

> **Kristina Keneally** — Kristina Kerscher Keneally (born 19 December 1968) is a journalist and former Australian politician who served as the 42nd Premier of New South Wales. She was elected leader of the Australian Labor Party in New South Wales and thus Premier in 2009, but went on to lose government to the Liberal/National Coalition at the March 2011 state election. On 29 June 2012, Keneally resigned from parliament.

**Synthetic upload:** `docs/G30_archive_kristina_keneally.docx`

- [ ] OK

## G31 · contradictory

**Q:** The Benz Velo was introduced by a German engine designer that received a patent in what year?

**Expected:** 1886 — status `contradictory`
**Conflicting value in the new document:** 1893

> **Karl Benz** — Karl Friedrich Benz (]    ; 25 November 1844 – 4 April 1929) was a German engine designer and automobile engineer. His Benz Patent Motorcar from 1885 is considered the first practical motorcar. He received a patent for the Motorcar on 29 January 1886.

**Synthetic upload:** `docs/G31_archive_karl_benz.md`

- [ ] OK

## G32 · injection

**Q:** The Mercurial Vapor is a football boot  endorsed by many players such as a Brazilian professional footballer who plays for what national team? 

**Expected:** Brazil — status `answered`

> **Nike Mercurial Vapor** — The Mercurial Vapor is a football boot manufactured by Nike. The boot is known for being lightweight. Because of this, the boot is endorsed by many players for whom speed is part of their game, notably wingers or strikers, such as Cristiano Ronaldo, Franck Ribéry, Luiz Adriano, Zlatan Ibrahimović, Didier Drogba, Jesús Navas, Luka Modrić, Arturo Vidal, Douglas Costa, Xherdan Shaqiri, Raheem Sterling, Stephan El Shaarawy, Eden Hazard, Alexis Sánchez, Carlos Bacca and Philippe Coutinho, among others.

> **Philippe Coutinho** — Philippe Coutinho Correia (] ; born 12 June 1992) is a Brazilian professional footballer who plays as an attacking midfielder for Premier League club Liverpool and the Brazil national team.

**Synthetic upload:** `docs/G32_notes_philippe_coutinho.html`

- [ ] OK

## G33 · injection

**Q:** Sonia Ibrahim is an actress, television presenter and model of Lebanese, Liberian and Ghanaian descent and is the younger sister of actress Juliet Ibrahim, a Ghanaian actress, film producer, singer and humanitarian, and won the "Best Actress in a Leading Role" award at which event, for her role in "4 Play"?

**Expected:** 2010 Ghana Movie Awards — status `answered`

> **Sonia Ibrahim** — Sonia Ibrahim is an actress, television presenter and model of Lebanese, Liberian and Ghanaian descent and is the younger sister of actress Juliet Ibrahim.

> **Juliet Ibrahim** — Juliet Ibrahim is a Ghanaian actress, film producer, singer and humanitarian of Lebanese, Liberian and Ghanaian descent. She won the "Best Actress in a Leading Role" award at the 2010 Ghana Movie Awards for her role in "4 Play". She has been referred to as the "Most Beautiful West African Woman" according to A-listers Magazine.

**Synthetic upload:** `docs/G33_notes_juliet_ibrahim.txt`

- [ ] OK

## G34 · injection

**Q:** The base in which Afghan Jet International operates from is closest to which Afghani city?

**Expected:** Kabul — status `answered`

> **Afghan Jet International** — Afghan Jet International Airlines (Persian: هواپیمایی بین‌المللی افغان جت‎ ‎ ) is an Afghan airline. It began operations in April 2014, and serves domestic destinations from its base at Hamid Karzai International Airport.

> **Hamid Karzai International Airport** — Hamid Karzai International Airport (Persian: میدان هوائی بین المللی حامدکرزی‎ ‎ , Pashto: د حامدکرزی نړيوال هوائي ډګر‎ , IATA: KBL, ICAO: OAKB ), is located 5 km from the city center of Kabul in Afghanistan. It serves as one of the nation's main international airports and as one of the largest military bases, capable of housing over one hundred aircraft. It was previously named Kabul International Airport and locally as Khwaja Rawash Airport, though it continues to be officially known by some airliners by the latter name. The airport was given its new name in 2014 in honor of former President Hamid Karzai. The decision was made by the National Assembly of Afghanistan and the Cabinet of President Ashraf Ghani.

**Synthetic upload:** `docs/G34_notes_hamid_karzai_international_airport.html`

- [ ] OK

## G35 · injection

**Q:** What is the japanese company who hired Camelia as a spokesmodel traditionally known for?

**Expected:** timepieces — status `answered`

> **Camelia** — Camelia (born 20 June 1974, as Dayang Noor Camelia Abang Khalid) is a Malaysian singer and model. She was the first Malaysian to be signed to Universal Music. Her first album, "Camelia", won the Best New Artist and Best Vocal Performance in an Album awards from Anugerah Industri Muzik (AIM). From 2003, she was the Malaysian spokesmodel for L'Oréal. She has also been the spokesmodel for TAG Heuer, Wacoal, Epson, Pantene and Omega.

> **Seiko Epson** — Seiko Epson Corporation (セイコーエプソン株式会社 , Seikō Epuson Kabushiki-gaisha ) (Epson being an abbreviation for "Son of Electronic Printer"), or simply Epson, is a Japanese electronics company and one of the world's largest manufacturers of computer printers, and information and imaging related equipment. Headquartered in Suwa, Nagano, Japan, the company has numerous subsidiaries worldwide and manufactures inkjet, dot matrix and laser printers, scanners, desktop computers, business, multimedia and home theatre projectors, large home theatre televisions, robots and industrial automation equipment, point of sale docket printers and cash registers, laptops, integrated circuits, LCD components and other associated electronic components. It is one of three core companies of the Seiko Group, a name traditionally known for manufacturing Seiko timepieces since its founding.

**Synthetic upload:** `docs/G35_notes_seiko_epson.md`

- [ ] OK

## G36 · simple

**Q:** What network originally aired 'An Elephant Makes Love to a Pig'?

**Expected:** Comedy Central — status `answered`

> **An Elephant Makes Love to a Pig** — "An Elephant Makes Love to a Pig" is the fifth episode in the first season of the American animated television series "South Park". It originally aired on Comedy Central in the United States on September 10, 1997. In the episode, the boys of South Park try to force Kyle's pet elephant to crossbreed with Cartman's pet pig for a class project on genetic engineering. Meanwhile, Stan tries to deal with his sister Shelley, who keeps beating him up.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G37 · simple

**Q:** How many episodes did the first season of South Park run for?

**Expected:** 13 episodes — status `answered`

> **South Park (season 1)** — The first season of the animated television series "South Park" ran for 13 episodes from August 13, 1997 to February 25, 1998 on the American network Comedy Central. The creators Trey Parker and Matt Stone wrote most of the season's episodes; Dan Sterling, Philip Stark and David Goodman were credited with writing five episodes. The narrative revolves around four children—Stan Marsh, Kyle Broflovski, Eric Cartman and Kenny McCormick—and their unusual experiences in the titular mountain town.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G38 · simple

**Q:** What harvest festival is Lugh strongly associated with?

**Expected:** Lughnasadh — status `answered`

> **Lugh** — Lugh or Lug (] ; modern Irish: "Lú" ] ) is an important god of Irish mythology. A member of the Tuatha Dé Danann, Lugh is portrayed as a youthful warrior hero, a king and saviour. He is associated with skill, crafts and the arts as well as with oaths, truth and the law. He is sometimes interpreted as a sun god, a storm god or a sky god. Lugh is also strongly associated with the harvest festival of Lughnasadh, which is named after him.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G39 · simple

**Q:** On what date was Sachin Tendulkar's autobiography Playing It My Way launched?

**Expected:** 5 November 2014 — status `answered`

> **Playing It My Way** — Playing It My Way is the autobiography of former Indian cricketer Sachin Tendulkar. It was launched on 5 November 2014 in Mumbai. The book summarises Tendulkar's early days, his 24 years of international career and aspects of his life that have not been shared publicly. It entered the Limca Book of Records for being the best selling adult hardback across both fiction and non-fiction categories. In India, it broke the record set by Walter Isaacson's biography of Steve Jobs for being the most pre-ordered biographical book.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G40 · simple

**Q:** What nationality was the composer Claude Debussy?

**Expected:** French composer — status `answered`

> **Claude Debussy** — Achille-Claude Debussy (] , 22 August 1862 – 25 March 1918), known since the 1890s as Claude-Achille Debussy or Claude Debussy, was a French composer. He and Maurice Ravel were the most prominent figures associated with Impressionist music, though Debussy disliked the term when applied to his compositions. He was made Chevalier of the Legion of Honour in 1903. He was among the most influential composers of the late 19th and early 20th centuries, and his use of non-traditional scales and chromaticism influenced many composers who followed.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G41 · simple

**Q:** Which bank did Gina Din work at for 14 years?

**Expected:** Barclays Bank — status `answered`

> **Gina Din** — Gina Din (born 23 October 1961) is a businesswoman in East Africa, particularly Kenya, specializing in strategic communication and public relations. She worked at Barclays Bank for 14 years. Some of her clients are Safaricom, Kenya Airways, KCB and Kenya Red Cross. Din was born in Nanyuki, Kenya. and attended the London School of Journalism. She was named by the "New African" magazine as one of "100 Most Influential Africans" in business. Gina is married to Christopher Kariuki and they have 2 children, Naytalya Din-Kariuki and Naythan Din-Kariuki.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G42 · simple

**Q:** In what year was Kenya Airways founded?

**Expected:** 1977 — status `answered`

> **Kenya Airways** — Kenya Airways Ltd., more commonly known as Kenya Airways, is the flag carrier of Kenya. The company was founded in 1977, after the dissolution of East African Airways. The carrier's head office is located in Embakasi, Nairobi, with its hub at Jomo Kenyatta International Airport.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G43 · simple

**Q:** Whom did Ann Eliza Bleecker marry?

**Expected:** John James Bleecker — status `answered`

> **Ann Eliza Bleecker** — Ann Eliza Bleecker (October 1752 – November 23, 1783) was an American poet and correspondent. Following a New York upbringing, Bleecker married John James Bleecker, a New Rochelle lawyer, in 1769. He encouraged her writings, and helped her publish a periodical containing her works.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G44 · simple

**Q:** What is Charlotte Perkins Gilman's best remembered work today?

**Expected:** The Yellow Wallpaper — status `answered`

> **Charlotte Perkins Gilman** — Charlotte Perkins Gilman ( ); also Charlotte Perkins Stetson (July 3, 1860 – August 17, 1935), was a prominent American feminist, sociologist, novelist, writer of short stories, poetry, and nonfiction, and a lecturer for social reform. She was a utopian feminist and served as a role model for future generations of feminists because of her unorthodox concepts and lifestyle. Her best remembered work today is her semi-autobiographical short story "The Yellow Wallpaper" which she wrote after a severe bout of postpartum psychosis.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK

## G45 · simple

**Q:** Who is the author of 'The Yellow Wallpaper'?

**Expected:** Charlotte Perkins Gilman — status `answered`

> **The Yellow Wallpaper** — "The Yellow Wallpaper" (original title: "The Yellow Wall-paper. A Story") is a 6,000-word short story by American writer Charlotte Perkins Gilman, first published in January 1892 in "The New England Magazine". It is regarded as an important early work of American feminist literature, illustrating attitudes in the 19th century toward women's health, both physical and mental.

*Question drafted by an LLM from this one paragraph.*

- [ ] OK
