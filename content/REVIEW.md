# Reviewing an AI drafted course

Every file in `content/courses/` is written by the model with `reviewed: false`.
Nothing in these files is loaded into the site until a person has read it and
flipped that flag. Do not flip it on trust, on a skim, or because the JSON
parsed.

## Checklist

Read every lesson in full, in order. Do not skip to the quizzes.

- [ ] Every factual claim is true. Check anything about a protocol, standard,
      regulation, law, framework or definition.
- [ ] Every tool, package, command, flag, file extension and API named in the
      lesson is real. Run the commands yourself. If a command does not work as
      written, fix the text or cut the lesson.
- [ ] No invented version numbers, statistics, prices, dates, job titles or URLs.
- [ ] The code, commands and steps would actually work on a clean machine.
- [ ] Language is plain and beginner friendly. Expand any unexplained jargon.
- [ ] Nigerian and African examples are accurate and not a thin veneer on
      generic content.
- [ ] Each quiz has exactly one clearly correct answer out of four, the
      `quiz_correct_index` points at that answer, and `quiz_feedback` explains
      why it is right.
- [ ] The distractors are plausible but genuinely wrong. A quiz with two
      arguable answers is broken.
- [ ] Lesson titles and the course description match what the content
      actually teaches.

## Extra care for cybersecurity

- [ ] Nothing in the lesson could help someone attack a system they do not own
      or have written permission to test. Practical attack techniques must be
      framed as authorised testing, and the lesson must say so.
- [ ] No live credentials, real target addresses, real exploit payloads aimed at
      a named product, or guidance for evading detection.
- [ ] Defensive advice is accurate. A wrong recommendation here is worse than
      no recommendation.
- [ ] Tool names, default ports and command syntax are correct for the version
      named, and you have checked whether that version is current.

## Finishing

Edit the lesson text directly in the JSON if anything is wrong. Then set:

```json
"reviewed": true
```

Run `python manage.py load_reviewed_courses` afterwards to load it.
