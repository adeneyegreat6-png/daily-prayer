# Daily Prayer — daily routine (followed by the scheduled task)

Goal: every day, publish one new ~75–80s prayer video (YouTube video + Short, Facebook Reel, Instagram Reel, TikTok) to the Metricool brand **"Daily prayer"**
(blogId `7942366`, timezone Europe/London) at **06:30 UK time the next morning**.

## 1. Pick today's prayer
- Look at `days/*.json`. The next day number = highest `day` + 1.
- Prayer type rotation (cycle in order, skip any used in the last 14 days):
  Protection, Guidance, Provision, Healing, Peace, Strength, Wisdom, Gratitude, Forgiveness,
  Family, Favour, Breakthrough, Anxiety, Faith, Purpose, Rest, Courage, Restoration, Fresh Start, Hope.
- Title is always **"Prayer for <Type>"** (e.g. "Prayer for Protection"). Never write "Day N" anywhere
  (not on screen, not on thumbnails, not in captions).
- `bg`: 1 on odd days, 2 on even days.
- Choose a fitting Bible verse (KJV, quoted exactly — verify the wording) not used in the last 60 days.
- Write an original prayer: 9–11 lines, ~120 words, each line ≤ 25 words, first person, warm, ends with
  "In Jesus' name I pray." (the script adds "Amen").

## 2. Write `days/dayNN.json`
Same fields as `days/day01.json`: day, bg, prayer_type, thumb_line1 ("PRAYER FOR"),
thumb_line2 (type in caps, e.g. "PROTECTION"; keep ≤ 14 chars or shorten), thumb_sub ("Pray along with me"),
reference, reference_spoken (words, e.g. "Psalm ninety-one, verses one and two."), translation "KJV",
verse (display, keep "LORD" small caps style as LORD), verse_spoken (list of 1–3 sentences, "Lord" not "LORD"),
prayer (list of lines), theme (short phrase).

## 3. Render
```
bash scripts/setup.sh
python3 scripts/make_prayer.py days/dayNN.json out/dayNN
```
Takes ~13 min. Check one frame of each video + both thumbnails visually before posting.

## 4. Captions
Write `out/dayNN/<slug>_captions.md` following `days/day01_captions.md`:
YouTube title "Prayer for <Type> | <hook> (<Reference>)", description with verse, 2–3 sentence summary,
timestamps (00:00 title, "Let us pray" and "Amen" times from the .srt), CTA, hashtags; Shorts title
"Prayer for <Type> 🙏 #shorts #prayer"; Facebook caption.

## 5. Publish media (public URLs)
Media lives on the orphan branch `media`, which holds only the last 3 days of files (force-pushed,
so the repo doesn't grow). Copy the two MP4s + `_thumbnail_16x9.jpg` there and push. URLs:
`https://raw.githubusercontent.com/<owner>/daily-prayer/media/<file>`
Check each URL returns HTTP 200 before scheduling (curl -sI may be blocked in the sandbox; Metricool will
report an error if the URL is bad).

## 6. Schedule in Metricool (brand 7942366), date = next day 06:30 Europe/London
- YouTube video: media = 16x9 mp4, videoThumbnailUrl = thumbnail jpg (drop it if Metricool returns
  VIDEO_THUMBNAIL_NOT_APPLICABLE), youtubeData {title, type "video", privacy "public", madeForKids false,
  category "NONPROFITS_ACTIVISM", tags}, text = YouTube description.
- YouTube Short: media = 9x16 mp4, youtubeData {title = Shorts title, type "short", privacy "public", madeForKids false}.
- Facebook Reel (always — the Daily prayer brand has its Facebook Page connected):
  media = 9x16 mp4, facebookData {type "REEL", title = prayer type}, text = Facebook caption.
- Instagram Reel (always — @every.day.prayer): media = 9x16 mp4, videoCoverMilliseconds 2000,
  instagramData {type "REEL", showReelOnFeed true, isAiGenerated false}, text = Facebook caption
  ("Follow the page" → "Follow", add #ChristianReels).
- TikTok: first call getBrandSettings and check the "Daily prayer" brand has `tiktokData`. If it does NOT,
  skip TikTok and report "TikTok not connected to the Daily prayer brand". If it does: media = 9x16 mp4,
  tiktokData {privacyOption "PUBLIC_TO_EVERYONE", title = "Prayer for <Type>", autoAddMusic false,
  isAigc false, comments/duet/stitch enabled}, text = TikTok caption (short: title, one verse line with
  reference, "Pray along and type AMEN.", 5–6 hashtags incl. #ChristianTok).
- Captions file gets an extra "## TikTok" section with that caption.
- First comment (every post): set `firstCommentText` on all five posts. Write one per platform, tied to
  today's prayer type, and add a "## First comments" section to the captions file listing them:
  - YouTube video + Short: an engagement question about the theme + "I'll pray over every comment today. 🙏"
    + the verse snippet and reference (e.g. "What's taking your peace right now? Write it below and I'll pray
    over every comment today. 🙏 'Thou wilt keep him in perfect peace…' Isaiah 26:3").
  - Facebook + Instagram: "Tag someone who needs <theme> today." + "Drop a 🙏 if you prayed along." +
    "New prayer every morning at 6:30."
  - TikTok: one short line, e.g. "What do you need <theme> for today? Comment it and we'll pray together 🙏".
  - No "Day N", no links, ≤ 300 characters. If Metricool rejects the first comment for a network, schedule
    that post again without `firstCommentText` and report which network didn't take it.

## 7. Commit
Commit `days/dayNN.json` and `days/dayNN_captions.md` to `main` and push.
