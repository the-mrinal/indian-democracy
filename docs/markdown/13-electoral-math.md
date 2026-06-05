# Electoral Systems: FPTP, STV & the Math

<p class="lede">India uses <strong>two</strong> different electoral systems side by side. First-Past-The-Post (FPTP) for everything you vote in directly — Lok Sabha, State Assembly, Panchayat. Single Transferable Vote with Proportional Representation (STV-PR) for the indirect elections — Rajya Sabha, Legislative Councils, President, Vice-President. The two produce very different mathematical pathologies. Understanding both is the difference between reading election results and reading them <em>well</em>.</p>

<div class="chapter-meta">
  <span><strong>Reading time:</strong> ~15 min</span>
  <span><strong>Pairs with:</strong> Laxmikanth, Electoral System chapter · Lokniti/CSDS election studies · Milan Vaishnav, <em>When Crime Pays</em></span>
</div>

## 1 · First-Past-The-Post (FPTP)

### 1.1 The rule

In each single-member constituency, **the candidate with the most votes wins** — regardless of whether they cross 50 %. That is the entire rule. There is no second round, no preferential ballot, no quota.

### 1.2 Where FPTP is used

- **Lok Sabha** (543 constituencies)
- **State Legislative Assemblies** (60 to 500 seats each)
- **Local bodies** — Panchayats and Municipalities

### 1.3 The vote-share / seat-share distortion

FPTP **magnifies pluralities into majorities** and **wastes votes** that don't help elect the winner. Famous Indian illustrations:

- **BJP, 2019 LS**: ~37.4 % national vote share → **303 LS seats** (55.8 % of the House).
- **INC, 2014 LS**: 19.3 % national vote share → just **44 LS seats** (8.1 % of the House) — Congress's worst-ever LS performance; UPA total of 59 fell *below* the 55-seat LOP threshold ([source](https://en.wikipedia.org/wiki/2014_Indian_general_election)).
- **BSP, 2014 LS**: 4.1 % national vote → **0 seats**. (Vote spread thinly across many constituencies — none won.)
- **DMK, 2024 LS**: ~22 seats from Tamil Nadu — a near-clean sweep because DMK concentrated its 5-6% national vote in one state.

The pattern: **regional concentration wins seats; dispersed vote wastes**.

### 1.4 Wasted vote phenomenon

In FPTP, **every vote for a losing candidate, and every vote for a winning candidate beyond what they needed**, is "wasted" — does not affect the result. India's "national vote share" is therefore a misleading aggregate: there is no national race, only 543 separate FPTP contests.

### 1.5 Why India sticks with FPTP

- **Simplicity** — voter sees one button, picks one candidate.
- **Single-member constituency = a "representative for me"** — geographic accountability is real.
- **Stability** — FPTP tends to produce single-party majorities (mostly true between 1952–1989 and 2014–2019; mixed during the coalition era 1989–2014 and again from 2024).
- **Path dependence** — switching is hard once parties' organisational structures have evolved around it.

## 2 · Single Transferable Vote with Proportional Representation (STV-PR)

### 2.1 Where STV-PR is used

- **Rajya Sabha** — elected by MLAs of each state.
- **Legislative Councils** in the 6 states that have them — elected partly by MLAs, partly by local bodies, partly by graduates, partly by teachers.
- **President** — elected by an Electoral College of MPs + MLAs with weighted vote values.
- **Vice-President** — elected by all MPs (elected + nominated).

### 2.2 The rule

Each elector **ranks the candidates** in order of preference. To win, a candidate must reach a **quota** — usually the **Droop quota**:

> **Quota = (Total valid votes ÷ (Number of seats + 1)) + 1**

Process:

1. **First-preference votes** are counted for each candidate.
2. Any candidate exceeding the quota is **declared elected**.
3. The winner's **surplus** votes (anything above the quota) are transferred to next-preferences, using a calculated "**transfer value**."
4. If no candidate has reached the quota, the candidate with the **fewest votes is eliminated** and their votes redistributed by next preferences.
5. Iterate until all seats are filled.

### 2.3 A small worked example — Rajya Sabha

Suppose a state has **5 RS seats** to fill, and **120 MLAs** to vote.

- Quota = (120 ÷ 6) + 1 = **21**.
- Each candidate needs **21 first-preference votes** to win outright.
- If a candidate gets 35 first-preferences, the **surplus of 14** is redistributed (with a transfer value < 1).
- If no candidate hits quota, the lowest is eliminated; their votes go to the next preference.

### 2.4 Why STV is "proportional"

If party A holds 60 % of MLA support and party B holds 40 %, on a 5-seat election:

- A's share of the quota: 60 % × 5 = 3 seats (roughly).
- B's share: 40 % × 5 = 2 seats (roughly).

So party seat-share **tracks vote-share** almost exactly — a sharp contrast to FPTP. This is why Rajya Sabha composition tends to reflect the *state-by-state* political landscape more accurately than the Lok Sabha reflects the *national* one.

## 3 · The President's election — STV with weighted values

A unique twist on STV. The President is elected by an Electoral College in which **votes are not equal** — they are weighted to balance:

1. **Uniformity of representation between states** (proportional to population).
2. **Parity between the Union (MPs) and the States (MLAs) as a whole**.

### 3.1 The formulas (re-stated from Chapter 5)

> **Value of one MLA's vote** = (State's population per 1971 Census ÷ Number of elected MLAs of that State) ÷ 1000
>
> **Value of one MP's vote** = (Total value of all MLA votes of all States) ÷ (Total number of elected MPs of both Houses)

### 3.2 Worked example — UP's 403 MLAs

UP's 1971 population was **8,38,49,905**. Elected MLAs = **403**.

- MLA vote value = 83,849,905 ÷ 403 ÷ 1000 ≈ **208**.
- So one UP MLA's vote = 208 vote units.
- Tamil Nadu (1971 pop: 4,11,99,168; 234 MLAs): vote value = 41,199,168 ÷ 234 ÷ 1000 ≈ **176**.
- Sikkim (1971 pop: 2,09,843; 32 MLAs): vote value = 209,000 ÷ 32 ÷ 1000 ≈ **7**.

### 3.3 The 2022 election numbers

| Metric | Value |
|---:|:---|
| Total electors | 4,809 (~771 MPs + 4,038 MLAs across 28 states + Delhi/Puducherry/J&K UTs) |
| MP vote value | 700 |
| Total vote value | 10,86,431 |
| Murmu votes | 2,161 (vote value: **5,77,777**) |
| Sinha votes | 1,058 (vote value: **2,61,062**) |

Murmu won by a margin of **2,96,626** vote-value units ([source](https://en.wikipedia.org/wiki/2022_Indian_presidential_election)).

### 3.4 Why 1971 census?

Frozen by the **42nd Amendment, 1976** and **extended by the 84th Amendment, 2001** until "the first census after 2026." This anchors the Electoral College in a uniform population baseline regardless of subsequent demographic shifts — so a UP MLA's vote weight today reflects UP's *1971* population, not 2026.

## 4 · Delimitation — drawing the constituencies

A **Delimitation Commission** redraws constituency boundaries after each census. There have been **four** Indian Delimitation Commissions: **1952, 1962, 1973, 2002** ([source](https://en.wikipedia.org/wiki/Delimitation_Commission_of_India)).

### 4.1 The freeze

The state-wise allocation of Lok Sabha seats was **frozen on 1971 census data** by the **42nd Amendment, 1976**, and the freeze was **extended by the 84th Amendment, 2001 until "the first census after 2026"**. The **87th Amendment, 2003** allowed intra-state boundary changes using **2001 census data**, but **without changing total seats per state**.

### 4.2 The 2026 fight

The first post-2026 census is scheduled for **1 March 2027**. If state-wise reapportionment follows on 2027 population:

- **Northern states** (UP, Bihar, Rajasthan, MP) would **gain** seats.
- **Southern states** (TN, Kerala, Karnataka, AP) would **lose** share.

A government attempt to push delimitation legislation early — the **Constitution (131st Amendment) Bill, 2026**, **UT Laws (Amendment) Bill, 2026**, and **Delimitation Bill, 2026**, introduced 16 April 2026 — saw the **131st Amendment Bill defeated 298–230**, short of the 352-vote 2/3 majority needed.

## 5 · Reservation of seats

### 5.1 SC/ST reservation

Under **Articles 330 and 332**, seats are reserved for Scheduled Castes and Scheduled Tribes in the Lok Sabha and State Assemblies **in proportion to their population** in that state. Currently in the Lok Sabha:

- **SC reserved seats: 84**
- **ST reserved seats: 47**

Reservation was **extended until 25 January 2030** by the **104th Amendment** (effective 25 January 2020), which also **abolished the Anglo-Indian nominated seats** (Articles 331 and 333).

### 5.2 Women's reservation — Nari Shakti Vandan Adhiniyam

The **106th Amendment, 2023** reserves **one-third of seats for women** in the Lok Sabha, State Legislative Assemblies, and the Delhi Legislative Assembly, including one-third within SC/ST reserved seats.

- Passed Lok Sabha **454–2** on 20 September 2023.
- Passed Rajya Sabha **214–0** on 21 September 2023.
- President's assent **28 September 2023**.
- Centre notified the law into force on **16 April 2026**.
- **Article 334A** stipulates the reservation will commence only **after a delimitation exercise based on the first census published after the Act's commencement**. The next census is scheduled for **1 March 2027**.
- Earliest realistic application: **2029 Lok Sabha election** (could slip further).

The reservation will be **rotated** — different constituencies will become women-reserved in successive election cycles. Operational duration: **15 years**, extendable by Parliament.

## 6 · Anti-Defection — the math of party loyalty (10th Schedule)

The **Tenth Schedule** (inserted by the **52nd Amendment, 1985**) disqualifies a legislator on the following grounds:

1. **Voluntarily giving up party membership** — including by conduct, not only by formal resignation.
2. **Voting or abstaining against a party whip** without prior permission (unless condoned within 15 days).
3. **An independent** elected legislator joining any political party after election.
4. **A nominated member** joining a political party after 6 months from taking the seat.

The **91st Amendment, 2003** removed the "split" exception that had previously protected defections by **one-third** of a legislature party. Only **"merger"** — requiring **two-thirds of the legislature party** plus formal merger with another party — is now an exempt route.

The **Speaker / Chairperson** decides disqualification (subject to judicial review per ***Kihoto Hollohan v. Zachillhu*, 1992***). In *Keisham Meghachandra Singh v. Manipur Speaker* (2020), the SC suggested decisions should be made within **3 months** — guidance, not statutorily binding.

Two 2024 high-profile cases — the **Shiv Sena split** (Speaker held Shinde faction = "real Shiv Sena" on 10 January 2024) and the **NCP split** (Speaker held Ajit Pawar faction = "real NCP" on 15 February 2024) — illustrate how the law has effectively been read down by partisan Speakers.

## 7 · "Vote-share vs seat-share" — the cheat sheet

| Phenomenon | Why it happens |
|---|---|
| Big national vote shares → outsized seat counts | FPTP's "winner takes all" magnifies pluralities |
| Small concentrated vote → big seats | DMK, TMC, BJD do this well — regional concentration |
| Big dispersed vote → small seats | BSP's classic problem — votes everywhere, wins nowhere |
| Anti-incumbency in a strong-leader system | Can rebalance dramatically (2024 UP) |
| Independent candidates' votes | Almost always wasted under FPTP |

## 8 · Three reform proposals that recur

The Indian electoral debate has three perennial reform candidates:

1. **Proportional Representation (PR)** — replace FPTP for the Lok Sabha with PR (probably MMP, mixed-member proportional). Would make vote-share and seat-share match more closely; would weaken single-party dominance; would also weaken accountability to a specific constituency. Periodically recommended (Law Commission 1999 — partial; National Commission to Review the Working of the Constitution 2002).
2. **Right to Recall** — let voters recall their MP/MLA mid-term. Adopted at panchayat level in some states (MP, Chhattisgarh, Bihar). No serious push at Lok Sabha level.
3. **One Nation, One Election** — synchronise Lok Sabha and Assembly elections to a single 5-year cycle. The Ram Nath Kovind Committee Report (March 2024) recommended a phased implementation; a Constitution Amendment Bill was tabled in December 2024. Implementation is politically contentious and constitutionally complex.

→ Continue with **[Chapter 14: Local Self-Government — Panchayats & Nagar Palikas](14-local-government.html)**.

## Sources

<div class="sources">
  <ul>
    <li><a href="https://en.wikipedia.org/wiki/Electoral_College_(India)">Electoral College — President's election math</a>.</li>
    <li><a href="https://en.wikipedia.org/wiki/2022_Indian_presidential_election">2022 Presidential election — vote values</a>.</li>
    <li><a href="https://en.wikipedia.org/wiki/Delimitation_Commission_of_India">Delimitation Commission of India</a>.</li>
    <li><a href="https://en.wikipedia.org/wiki/One_Hundred_and_Sixth_Amendment_of_the_Constitution_of_India">106th Amendment — Nari Shakti Vandan Adhiniyam</a>.</li>
    <li><a href="https://www.lokniti.org/">Lokniti / CSDS — election studies</a>.</li>
    <li>Yogendra Yadav, "<em>Making Sense of Indian Democracy</em>" (Permanent Black, 2020) — Ch. on FPTP and the "third electoral system".</li>
    <li>M. Laxmikanth, <em>Indian Polity</em>, Electoral System chapter.</li>
  </ul>
</div>
