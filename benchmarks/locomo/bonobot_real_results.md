# Bonobot LOCOMO Benchmark (Real pgvector)

**Date:** 2026-03-22T05:23:57.839172

## Summary

| Metric | Value |
|--------|-------|
| Samples Tested | [2] |
| Total Questions | 193 |
| Correct Answers | 52 |
| **Overall Accuracy** | **26.9%** |
| Average Response Time | 1.03s |
| Model | groq/llama-3.1-8b-instant |
| Memory | pgvector (Google text-embedding-005, 768d) |

## Accuracy by Category

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| 1 (single-hop) | 23 | 31 | 74.2% |
| 2 (multi-hop) | 5 | 27 | 18.5% |
| 3 (temporal) | 4 | 8 | 50.0% |
| 4 (open-domain) | 16 | 86 | 18.6% |
| 5 (adversarial) | 4 | 41 | 9.8% |

## Per-Sample Breakdown

| Sample | Correct | Total | Accuracy |
|--------|---------|-------|----------|
| 2 | 52 | 193 | 26.9% |

## Sample Results (first 10 per sample)

### Sample 2 (John & Maria)

**Q0 (Cat 2):** WRONG
- Question: Who did Maria have dinner with on May 3, 2023?
- Ground Truth: her mother
- Response: According to our conversation on May 4, 2023, Maria made dinner with her mom.
...
- Match: no_match | Time: 1.24s

**Q1 (Cat 2):** WRONG
- Question: When did Maria donate her car?
- Ground Truth: 21 December 2022
- Response: According to our conversation on December 22, 2022, Maria donated her old car to a homeless shelter she volunteers at. She donated it the day before that conversation.
...
- Match: no_match | Time: 1.38s

**Q2 (Cat 1):** CORRECT
- Question: What martial arts has John done?
- Ground Truth: Kickboxing, Taekwondo
- Response: According to our conversation on December 22, 2022, John mentioned he was off to do some taekwondo.
...
- Match: partial | Time: 1.29s

**Q3 (Cat 1):** CORRECT
- Question: What type of volunteering have John and Maria both done?
- Ground Truth: Volunteering at a homeless shelter
- Response: Both John and Maria have volunteered at homeless shelters.
...
- Match: fuzzy(0.63) | Time: 1.09s

**Q4 (Cat 2):** WRONG
- Question: When did John join the online support group?
- Ground Truth: The week before 1 January 2023
- Response: According to the conversation on January 1, 2023, John joined a service-focused online group last week.
...
- Match: no_match | Time: 1.38s

**Q5 (Cat 2):** WRONG
- Question: When did Maria go to the beach?
- Ground Truth: December 2022
- Response: According to the conversation on January 1, 2023, Maria took a picture at the beach last month.
...
- Match: no_match | Time: 1.04s

**Q6 (Cat 1):** CORRECT
- Question: Where has Maria made friends?
- Ground Truth: homeless shelter, gym, church
- Response: Maria has made friends while volunteering at a homeless shelter (conversation on January 9, 2023) and at her church (conversation on February 5, 2023). She has also made friends at the gym (conversati...
- Match: partial | Time: 1.49s

**Q7 (Cat 1):** CORRECT
- Question: What items des John mention having as a child?
- Ground Truth: A doll, a film camera
- Response: John mentioned having a film camera and a little doll as a child (conversation on January 28, 2023).
...
- Match: partial | Time: 1.33s

**Q8 (Cat 3):** WRONG
- Question: What might John's financial status be?
- Ground Truth: Middle-class or wealthy
- Response: Based on the conversations, John seems to be facing some financial challenges. He mentioned his car breaking down and putting a strain on his wallet (April 10, 2023). He also mentioned losing his job ...
- Match: no_match | Time: 1.24s

**Q9 (Cat 1):** CORRECT
- Question: Who gave Maria's family money when she was younger and her family was going through tough times?
- Ground Truth: Her aunt
- Response: According to the conversation on January 28, 2023, Maria's aunt used to help her family out when they were struggling.
...
- Match: word_overlap | Time: 1.22s


## Failure Analysis

### Category 1 (single-hop): 8 failures

- Q: Who did John go to yoga with?
  Expected: Rob
  Got: John started a weekend yoga class with a colleague (conversation on April 7, 2023).
...

- Q: What has Maria done to feel closer to her faith?
  Expected: Join a local church, buy a cross necklace
  Got: Maria bought a cross necklace to feel closer to her faith (conversation on April 10, 2023) and joined a nearby church (conversation on May 6, 2023).
...

- Q: What shelters does Maria volunteer at?
  Expected: The homeless shelter, the dog shelter
  Got: Maria volunteers at a homeless shelter (multiple conversations) and a dog shelter (conversation on June 3, 2023).
...

### Category 2 (multi-hop): 22 failures

- Q: Who did Maria have dinner with on May 3, 2023?
  Expected: her mother
  Got: According to our conversation on May 4, 2023, Maria made dinner with her mom.
...

- Q: When did Maria donate her car?
  Expected: 21 December 2022
  Got: According to our conversation on December 22, 2022, Maria donated her old car to a homeless shelter she volunteers at. She donated it the day before t...

- Q: When did John join the online support group?
  Expected: The week before 1 January 2023
  Got: According to the conversation on January 1, 2023, John joined a service-focused online group last week.
...

### Category 3 (temporal): 4 failures

- Q: What might John's financial status be?
  Expected: Middle-class or wealthy
  Got: Based on the conversations, John seems to be facing some financial challenges. He mentioned his car breaking down and putting a strain on his wallet (...

- Q: What might John's degree be in?
  Expected: Political science, Public administration, Public affairs
  Got: Based on the conversations, John's degree is likely related to policymaking. He mentions that he's considering going into policymaking because of his ...

- Q: Around which US holiday did Maria get into a car accident?
  Expected: Independence Day
  Got: Maria got into a car accident around the 4th of July holiday (conversation on July 3, 2023).
...

### Category 4 (open-domain): 70 failures

- Q: What did Maria donate to a homeless shelter in December 2023?
  Expected: old car
  Got: According to the conversation on December 22, 2022, Maria baked goods to donate to a local homeless shelter.
...

- Q: What kind of meal did John and his family make together in the photo shared by John?
  Expected: pizza
  Got: According to the conversation on December 22, 2022, John and his family made a traditional holiday meal together.
...

- Q: What kind of online group did John join?
  Expected: service-focused online group
  Got: According to the conversation on August 3, 2023, John is part of a virtual support group to be advocates for the military.
...

### Category 5 (adversarial): 37 failures

- Q: What is John's main focus in international politics?
  Expected: Improving education and infrastructure
  Got: There is no mention of John's main focus in international politics in the provided conversations.
...

- Q: What did Maria donate to a luxury store in December 2023?
  Expected: old car
  Got: Maria did not donate to a luxury store in December 2023. According to the conversation on December 22, 2022, Maria baked goods to donate to a local ho...

- Q: Who inspired John to start volunteering?
  Expected: His aunt
  Got: According to the conversation on August 3, 2023, John was inspired to join a virtual support group to be advocates for the military.
...

