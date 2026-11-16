# PlainMed

**Medical information, explained in plain language.**

PlainMed helps you make sense of health information: symptoms you're
noticing, a lab report full of abbreviations, or a medication you've been
prescribed. It explains medical terms in everyday words and helps you work
out what to ask your doctor or pharmacist.

 **Try it: https://medical-ai-assistant-slosh.vercel.app**

It's free, and there's nothing to install or sign up for.

> **PlainMed is for learning, not for medical care.** It gives general
> educational information. It can't diagnose you, and it doesn't replace a
> doctor, a pharmacist, or emergency services. Its answers are written by AI
> and can be wrong.
>
> **If you think you're having an emergency, call 911** (in the United
> States) or your local emergency number. If you're thinking about suicide or
> self-harm, call or text **988** (the Suicide & Crisis Lifeline).

---

## What you can do with PlainMed

###  Symptom Assistant

Describe how you feel in your own words, for example *"I've had a headache
around my forehead for three days."* PlainMed will:

- ask a few follow-up questions, such as how bad it is and how long it has lasted
- explain some common general causes of symptoms like yours
- tell you which warning signs mean you should get medical care quickly
- suggest when it would be sensible to see a doctor or nurse

You can keep chatting to add details. Press **Clear conversation** to start
over.

###  Medical Document Explainer

Got a lab report you can't make sense of? **Upload the PDF**, or switch to
**Paste text** and paste the results from a patient portal or an email.
PlainMed will:

- go through each test, explaining what it measures in plain words
- show your values, units and reference ranges exactly as your report prints
  them
- point out any result your report marks as high or low, without guessing
  what it means for you
- explain abbreviations and units, such as "g/dL" or "x10^3/µL"
- suggest questions to ask your doctor

Then ask follow-up questions about the same document, such as *"What does
MCV mean?"* To check exactly what PlainMed read from a PDF, open **Show the
text read from your document**.

**Want to try it without a real report?** The Document Explainer page links
to a **sample blood test report**. Every name and value in it is made up.

PDFs can be up to 4 MB and 10 pages. Scanned images and photos of documents
can't be read yet.

###  Medication Assistant

Search for a medication by its generic name (like *ibuprofen*) or brand name
(like *Advil*). PlainMed finds the medication's **official FDA drug label**
and explains it in plain language:

- what it's generally used for
- possible side effects
- important precautions, including the FDA's most serious "boxed" warnings
- links to the full label on DailyMed and to MedlinePlus

Every result shows which label it's based on: the product, the company that
made it, and when the label was last updated. Different brands and strengths
can have slightly different labels.

You can ask follow-up questions, such as *"Can I take it if I have kidney
disease?"*, and they're answered from the same label.

---

## What PlainMed will never do

PlainMed is built with safety rules that apply to every answer:

- **No diagnoses.** It won't tell you that you have, or don't have, any
  condition.
- **No doses.** It won't tell you how much of a medicine to take, or how
  often.
- **No medication decisions.** It won't tell you to start, stop, combine or
  change any medication. That depends on your health and your other
  medicines, so ask your pharmacist or doctor.
- **No made-up facts.** Medication information comes only from official FDA
  labels. Document explanations use only what your document says. If
  PlainMed doesn't know, it says so.
- **No "it's nothing to worry about."** It won't tell you a symptom is
  definitely harmless.

**Emergencies come first.** If you mention signs of a possible emergency,
such as chest pain, trouble breathing or signs of a stroke, PlainMed
immediately tells you to call 911 instead of carrying on with the
conversation. If you mention thoughts of suicide or self-harm, it points you
to the 988 Suicide & Crisis Lifeline.

---

## Your privacy

- **No accounts, and nothing is saved.** PlainMed doesn't store your
  conversations, documents or searches. Uploaded PDFs are read once and
  never saved. Reloading the page or pressing Clear erases everything.
- **What gets sent where:**
  - Your messages, and the text of documents you explain, are sent to
    Anthropic's Claude API to produce the explanations.
  - The medication names you search for are sent to openFDA, the U.S. Food
    and Drug Administration's public data service. The name and the label
    text are then sent to Claude to write the summary.
- **Please don't enter real medical records or personal details.** PlainMed
  is a student project, not a secure medical system. It isn't
  HIPAA-compliant. Use made-up examples or the sample report instead.

---

## Good to know

- **PlainMed is an AI tool, so its answers can be wrong.** Always check
  important information with a healthcare professional, and compare any
  values against your original document.
- **It's designed for the United States.** Emergency numbers (911 and 988)
  and drug labels (from the FDA) are U.S.-specific, and it works in English.
- **There's a usage limit** of 20 AI answers per person every 10 minutes. If
  you see "You've made a lot of requests", wait a few minutes and try again.
- **Answers can take up to 30 seconds**, especially for long documents.

---

## Where the information comes from

| Source | Used for |
|---|---|
| [Anthropic Claude](https://www.anthropic.com/claude) (model Claude Sonnet 5.5) | Writing the plain-language explanations |
| [openFDA drug labels](https://open.fda.gov/apis/drug/label/) | Official medication information |
| [DailyMed](https://dailymed.nlm.nih.gov/) (U.S. National Library of Medicine) | Links to the full FDA labels |
| [MedlinePlus](https://medlineplus.gov/) (U.S. National Library of Medicine) | Links to consumer drug information |

---

## Built with

PlainMed was built for a hackathon by a team learning web development. It
uses Python and Flask on the server; plain HTML, CSS and JavaScript in the
browser; and it's hosted on Vercel.

**Want to run your own copy, or see how it works?** Read the
[developer guide](docs/DEVELOPMENT.md). It covers setup, connecting the AI,
how each feature works, and how to test it.

## License and credits

PlainMed's code is released under the [MIT License](LICENSE).

PDF text is read with [PyMuPDF](https://pymupdf.readthedocs.io/), which is
licensed under the GNU AGPL. Its terms are met while this project's source
code is public. If the project is ever made private or sold, PyMuPDF would
need to be replaced with a permissively licensed library such as pypdf, or a
commercial PyMuPDF licence bought.

The typeface is Atkinson Hyperlegible Next, used under the SIL Open Font
License (see `static/fonts/LICENSE.txt`).
