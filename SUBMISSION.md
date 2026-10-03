---
title: SafePlate: a menu checker for my friend with a peanut allergy, running on Gemma with no cloud
published: false
tags: devchallenge, weekendchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Weekend Challenge: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01)*

<!-- TODO: replace [Maya] and the story with your real friend, and change profile.json to match. -->

## What I Built

[Maya] has an anaphylactic peanut allergy and is also allergic to tree nuts and shellfish. Every time we eat out, the same thing happens. She reads the menu twice, then asks the server three questions, then orders the plain rice anyway. Peanuts hide in places you wouldn't expect: satay, pesto, "crunchy topping", the wok that cooked the last order.

**SafePlate** is a phone-friendly web page. She takes a photo of the menu and gets back every dish sorted into **Avoid**, **Ask first** and **Looks safe**, each with a reason. Each risky dish also comes with the exact question to ask the server, like *"Is the Kung Pao cooked in the same wok as other dishes?"* At a loud table she can tap **Read it to me** and hear the verdicts in an ElevenLabs voice instead of squinting at her phone.

## Demo

<!-- TODO: 30-second screen recording: snap menu → results -->

Real output from a test menu photo, on a laptop with no internet:

```
AVOID  Kung Pao Chicken        Ask: "Can you confirm the wok is cleaned between dishes?"
AVOID  Garlic Butter Scallops  (keyword safety net)
AVOID  Basil Pesto Pasta       Ask: "Do you offer a pesto without pine nuts?"
AVOID  Vegetable Spring Rolls  Ask: "What's in the sweet chili dip?"
SAFE   Steamed Jasmine Rice
```

Each photo takes about 13 seconds on my laptop.

## Code

{% github <your-username>/safeplate %}

Live version: <!-- TODO: your-app.onrender.com -->

It's two files that matter: `app.py` (about 110 lines, Python standard library only) and `index.html`. There's nothing to `pip install`.

## How I Built It

- **Gemma 3 4B** through **Ollama**. Gemma 3 is multimodal, so it reads the menu photo directly and I don't need a separate OCR step. It's 3.3 GB and runs on an ordinary laptop.
- **Structured output.** Ollama's `format` parameter holds Gemma to a JSON schema, so each dish always comes back with `verdict` set to `safe`, `ask` or `avoid`. That means no regex over free-form text.
- **A safety net that doesn't trust the model.** The 4B model is good, but "good" isn't enough for an allergy. In testing it rated *Garlic Butter Scallops* and *Tom Yum Goong (prawns)* as less than "avoid" for someone with a shellfish allergy. So after Gemma answers, a dumb keyword pass runs over the menu text. If the profile says `shellfish: shrimp, prawn, scallop…` and the text contains one of those words, the dish becomes **Avoid**, whatever the model said. The model handles nuance (sauces, cuisines, cross-contact), and the keywords guarantee the obvious cases. Any verdict the code doesn't recognise falls back to "ask", never to "safe".
- **One app, two places to run it.** If `GEMINI_API_KEY` is set, the same code calls **hosted Gemma 3 27B** through Google's Gemini API. That's how it runs on **Render's free tier**, which has no GPU: a `render.yaml` blueprint, no build step, and a password on the URL. Without the key it talks to local Ollama. Same prompt, same safety net, same model family.
- **A voice from ElevenLabs.** The verdicts become one short spoken summary ("Avoid: Kung Pao Chicken. Ask about the papaya salad: is the fish sauce made separately from nuts?"), sent to ElevenLabs' `eleven_flash_v2_5` model for low latency. Offline or without a key, it falls back to the browser's built-in speech, so the button always works.
- **Profile** in `profile.json`, editable from the UI: allergens, the keywords each one hides behind, and notes like "shared fryers matter".

## Why Does Open Innovation Matter?

- **Her health data stays with her.** A list of someone's life-threatening allergies is medical information. With a local open-weight model it never leaves the laptop. There's no vendor, no retention policy to read, and no account to make.
- **Private when it matters, convenient when it doesn't.** The hosted Render version is for convenience. Because Gemma is open-weight, she can run the same model on her own laptop and keep everything off servers she doesn't control. With a closed model that choice wouldn't exist.
- **It works where restaurants are.** Basements, patios and bad signal don't matter, because there's no network round trip at the table.
- **It costs nothing to run.** No API key and no per-photo bill, so she can check every menu without thinking about it.
- **I can swap models with one setting.** `MODEL=gemma3:12b` gives more accuracy on a bigger machine, and `gemma3:1b` works on a tiny one with pasted text. With a closed API I'd get one model at one price, and that price could change.
- **I can see and control the whole pipeline.** Because I own the inference call, I could force the JSON schema, set temperature to 0 and put my own deterministic check after the model. A closed chatbot would hand me an answer and ask me to trust it, and for an allergy I won't.

## What [Maya] said

<!-- TODO: hand it over, quote them here. Bonus points from the judges. -->

## Prize Categories

- Best Use of Gemma
- Best Use of Render
- Best Use of ElevenLabs
