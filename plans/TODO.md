PitchPulse prati sintetičku utakmicu “uživo” po minutama na studijskom dashboardu.

Sustav ne gleda samo rezultat. Gleda gdje ekipa propušta:

    * očite rupe (npr. prevelik pritisak / previše centaršuteva po desnom boku),
    * i manje, gotovo nevidljive greške (npr. sitni gubici lopte ili slabi dueli u sredini zbog jačeg protivničkog igrača).

Sve što se vidi na dashboardu dolazi iz izgeneriranog synthetic dataseta (eventi, zone, igrači, pritisak, dueli) — demo je namješten oko dvije pozicije / dvije priče (npr. desni bek + centralni vezni), da se cijeli pipeline jasno pokaže.

Kad se propusnost pojavi:

1. Alert — što curi i zašto je bitno
2. Savjet treneru — smjernice prema igračima koji trenutno propuštaju (kako držati bok, kada ulaziti u duel, kako smanjiti kontakt s dominantnim protivnikom)
3. Ako se problem nastavi — shortlist sa klupe: profili zamjena koji po “dosadašnjim” synthetic učincima odgovaraju tipu prijetnje (npr. zračni bek protiv bokova / duel-jači mid protiv pressera)
4. Fan view nije drugi proizvod — isti match intelligence, drugačiji trenutak i jezik:

trener/analitičar vide alerte tijekom razvoja situacije,
fanovi nakon zamjene dobiju “zašto je trener reagirao”: kratki rewind prozora oko zamjene (što je curilo, koji je potez povučen, je li rupa zatvorena).

Studio and coaching staff need assistant-style cues while the match is still unfolding: where the team is leaking, which flank is overloaded, and which smaller midfield mistakes are compounding under pressure from a stronger opponent.

PitchPulse ingests synthetic football events minute-by-minute, surfaces explainable tactical alerts on a live studio dashboard, and turns those gaps into coaching guidance and substitute profiles that fit the threat. The same match intelligence powers three experiences — Coach (alerts + how to fix it now), Analyst (patterns and evidence), and Fan (post-substitution explainers that show what the coach saw and why the change was made). The demo dataset is purpose-built around two clear positional storylines so every stage of the pipeline is visible end to end.

One-liner pipeline:

Live synthetic events → positional leak detection → explainable coaching alerts → bench profiles that can stop the threat → Coach / Analyst / Fan views from the same intelligence

Slightly longer variant (README / video voiceover):

PitchPulse watches a synthetic match as a live clock on a studio dashboard. It flags both obvious structural leaks — for example a right-flank overload of crosses and entries — and quieter individual breakdowns in midfield that are easy to miss in the moment. Each alert is grounded in generated event data (passes, duels, pressure, zone load) and comes with coaching guidance aimed at the players currently exposed. If the leak persists, PitchPulse proposes substitute profiles from a synthetic bench catalog whose prior-match traits match what the situation demands. Fans do not get a second-by-second coaching feed; instead, when a substitution is made, they get a clear windowed recap of the leak the coach reacted to and whether the change addressed it — personalized storytelling from the same underlying match intelligence.

Tagline
Primary:
From live leaks on the pitch to coaching calls — and the substitutes who can stop them

Alt (kraći):
See the leak. Guide the fix. Explain the sub.

Keywords

Football Analytics
Synthetic Match Intelligence
coaching alerts
tactical pressure
positional leaks
live match dashboard
substitute shortlist
explainable AI
Coach Analyst Fan
Azure OpenAI
Conversational AI Agent
multi-language storytelling