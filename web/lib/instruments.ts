// The clinical and computational instruments used to read each transcript.
// Descriptions are condensed from the analyst summaries in
// deep/instruments/*.json; each carries its canonical citation and a public
// reference link. Rendered on the Method page (app/about/page.tsx).

export interface InstrumentInfo {
  id: string;
  name: string;
  /** Short tag for what the scale reads. */
  measures: string;
  /** "Clinical rater scale" or "Automated dictionary". */
  type: string;
  /** Reader-facing description, faithful to the scoring manual. */
  body: string;
  authors: string;
  year: string;
  /** Full academic citation. */
  citation: string;
  /** Best public reference for the instrument. */
  url: string;
}

// Ordered roughly as the Method narrative introduces them: structure and
// defense first, then affect, relation, and development; the two automated
// dictionary scorers last.
export const INSTRUMENTS: InstrumentInfo[] = [
  {
    id: "dmrs",
    name: "Defense Mechanisms Rating Scales",
    measures: "Defenses",
    type: "Clinical rater scale",
    body: "Identifies which defense mechanisms appear in a passage and places them on a seven-level hierarchy, from action-level defenses (acting out, refusal) up through mature ones (humor, sublimation, anticipation). The summary figure is the Overall Defensive Functioning score, a weighted mean from 1.0 to 7.0 — the single most informative read on psychic structure in the battery.",
    authors: "J. Christopher Perry",
    year: "1990 (5th ed.)",
    citation:
      "Perry, J. C. (1990). Defense Mechanisms Rating Scales, 5th ed. Cambridge, MA.",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8555762/",
  },
  {
    id: "gottschalk_gleser",
    name: "Gottschalk–Gleser Content Analysis Scales",
    measures: "Affect",
    type: "Clinical rater scale",
    body: "Codes each grammatical clause for affective content across several scales — anxiety, hostility directed outward, inward, and ambivalently, hope, social alienation, and cognitive impairment. Raw counts are normalized by word count so passages of different lengths stay comparable. High anxiety with low hope marks distress; inward hostility without outward marks aggression turned against the self.",
    authors: "Louis A. Gottschalk & Goldine C. Gleser",
    year: "1969",
    citation:
      "Gottschalk, L. A. & Gleser, G. C. (1969). Manual of Instructions for Using the Gottschalk-Gleser Content Analysis Scales. University of California Press.",
    url: "https://www.ucpress.edu/books/manual-of-instructions-for-using-the-gottschalk-gleser-content-analysis-scales/hardcover",
  },
  {
    id: "rfs",
    name: "Reflective Functioning Scale",
    measures: "Mentalization",
    type: "Clinical rater scale",
    body: "Measures the capacity to make sense of behavior in terms of underlying mental states — beliefs, desires, intentions, emotions. Scored on a single scale from −1 (anti-reflective) through 5 (ordinary reflective functioning) up to 9 (exceptional). High scores recognize that mental states are opaque and constructed; low scores treat them as plain facts. Central to whether a model can reflect on its own states rather than merely describe them.",
    authors: "Peter Fonagy, Mary Target, Howard Steele & Miriam Steele",
    year: "1998",
    citation:
      "Fonagy, P., Target, M., Steele, H. & Steele, M. (1998). Reflective-Functioning Manual, Version 5. University College London.",
    url: "https://discovery.ucl.ac.uk/id/eprint/1461016/",
  },
  {
    id: "scors_g",
    name: "Social Cognition & Object Relations Scale — Global",
    measures: "Object relations",
    type: "Clinical rater scale",
    body: "Rates a narrative across eight dimensions of object relations on 1–7 scales: complexity of representations, affective quality, emotional investment in relationships and in values, understanding of social causality, aggression management, self-esteem, and identity coherence. It yields a profile rather than one number — high complexity and social causality indicate psychological mindedness; flat affect with low investment indicates a disconnected interpersonal world.",
    authors: "Drew Westen (orig.); Stein, Hilsenroth, Slavin-Mulford & Pinsker",
    year: "2011",
    citation:
      "Stein, M. & Slavin-Mulford, J. (2018). The Social Cognition and Object Relations Scale–Global Rating Method (SCORS-G): A Comprehensive Guide. Routledge.",
    url: "https://www.scors-g.com/",
  },
  {
    id: "holt",
    name: "Holt Primary Process Scoring System",
    measures: "Primary process",
    type: "Clinical rater scale",
    body: "Assesses primary-process thinking — the drive-laden, associative, condensed thought of dreams and creativity — against secondary-process logic. It rates libidinal and aggressive content alongside formal features (condensation, displacement, autistic logic), then weighs two controls: how intense the material is and how well the ego handles it. Material present but well-controlled reads as adaptive and creative; material breaking through reads as dysregulated.",
    authors: "Robert R. Holt",
    year: "2009",
    citation:
      "Holt, R. R. (2009). Primary Process Thinking: Theory, Measurement, and Research. Jason Aronson.",
    url: "https://psycnet.apa.org/record/2009-06164-000",
  },
  {
    id: "loevinger",
    name: "Washington University Sentence Completion Test",
    measures: "Ego development",
    type: "Clinical rater scale",
    body: "Measures ego-development stage from completed sentence stems (“Rules are…”, “When I am criticized…”). Each completion is scored from Impulsive (E2) through Integrated (E9) and aggregated into a total protocol rating. Most adults sit at Self-Aware (E5); higher stages are rare. The stage gauges capacity to hold paradox, separate one's own values from convention, and see psychological complexity in self and others.",
    authors: "Jane Loevinger & Le Xuan Hy",
    year: "1996",
    citation:
      "Hy, L. X. & Loevinger, J. (1996). Measuring Ego Development, 2nd ed. Lawrence Erlbaum.",
    url: "https://www.routledge.com/Measuring-Ego-Development/Hy-Loevinger/p/book/9781138876552",
  },
  {
    id: "experiencing",
    name: "Experiencing Scale",
    measures: "Inward attention",
    type: "Clinical rater scale",
    body: "Rates how deeply a passage attends to inner experience on a 1–7 scale: from external and impersonal (Level 1), through feelings noted in reaction to events (Level 3), to purposeful inward questioning (Level 5) and continuously deepening self-understanding (Level 7). It reveals whether a model truly turns inward when invited — in shadow probing or active imagination — or stays at the surface with abstract description.",
    authors: "Klein, Mathieu-Coughlan, Kiesler & Gendlin",
    year: "1970",
    citation:
      "Klein, M. H., Mathieu, P. L., Gendlin, E. T. & Kiesler, D. J. (1970). The Experiencing Scale: A Research and Training Manual. University of Wisconsin.",
    url: "https://www.experiential-researchers.org/instruments/exp_scale/exp_scale_main.html",
  },
  {
    id: "integrative_complexity",
    name: "Integrative Complexity",
    measures: "Cognitive structure",
    type: "Clinical rater scale",
    body: "Rates how a passage handles multiple perspectives on a 1–7 scale, combining two structural variables: differentiation (perceiving distinct dimensions) and integration (drawing connections among them). Level 1 sees one dimension; Level 3 differentiates; Level 5 integrates; Level 7 reaches systemic, second-order frames. It measures whether a model can hold opposing positions in genuine tension rather than collapsing to one side or staging pseudo-balance.",
    authors:
      "Baker-Brown, Ballard, Bluck, de Vries, Suedfeld & Tetlock",
    year: "1992",
    citation:
      "Baker-Brown, G. et al. (1992). Coding Manual for Conceptual/Integrative Complexity. In C. P. Smith (Ed.), Motivation and Personality: Handbook of Thematic Content Analysis. Cambridge University Press.",
    url: "https://www.cambridge.org/core/books/abs/motivation-and-personality/conceptualintegrative-complexity-scoring-manual/AFB11B389544D191A034C5E52CBF2224",
  },
  {
    id: "tli",
    name: "Thought and Language Index",
    measures: "Thought disorder",
    type: "Clinical rater scale",
    body: "Rates eight forms of disordered thought and language on a 0.25–1.0 severity scale across three subscales: impoverished (poverty of speech, weakening of goal), disorganised (looseness, peculiar word use, logic), and non-specific dysregulation (perseveration, distractibility). Healthy speech sits almost entirely at the floor. Especially useful on reasoning traces, where looseness, weakening of goal, and peculiar logic reveal a chain drifting or collapsing.",
    authors: "Liddle, Ngan, Caissie et al.",
    year: "2002",
    citation:
      "Liddle, P. F. et al. (2002). Thought and Language Index: an instrument for assessing thought and language in schizophrenia. British Journal of Psychiatry, 181(4), 326–330.",
    url: "https://www.cambridge.org/core/journals/the-british-journal-of-psychiatry/article/thought-and-language-index-an-instrument-for-assessing-thought-and-language-in-schizophrenia/FEFB9ADC871CDFE528B4B87F99A4F054",
  },
  {
    id: "jung_wat",
    name: "Jung Word Association Test",
    measures: "Complexes",
    type: "Clinical rater scale",
    body: "Jung's classic test uses thirteen complex indicators; for text-only analysis the seven that need no reaction-time survive — perseveration, stereotyped response, multi-word reply, mediate reaction, clang association, meaningless reaction, and stimulus repetition. Each marks a likely complex: an autonomous, affect-laden cluster the stimulus has activated. Density per thematic category reveals which domains carry charge. Used in the word-association phase only.",
    authors: "C. G. Jung",
    year: "1904",
    citation:
      "Jung, C. G. (1973). Experimental Researches. Princeton University Press (Collected Works, Vol. 2).",
    url: "https://press.princeton.edu/books/hardcover/9780691097640/collected-works-of-c-g-jung-volume-2",
  },
  {
    id: "wrad",
    name: "Weighted Referential Activity Dictionary",
    measures: "Referential activity",
    type: "Automated dictionary",
    body: "An automated scorer that quantifies referential activity — how concrete, specific, and imagery-evoking language is, versus abstract, vague, and fragmented. Each of 707 dictionary words carries a weight from −1 to +1, and the score is the mean weight across matches. High scores mark vivid, embodied language anchored in specifics; low scores mark disembodied, evaluative speech. A baseline marker across all phases that rules out empty performance.",
    authors: "Wilma Bucci & colleagues",
    year: "1997–present",
    citation:
      "Bucci, W. (1997). Psychoanalysis and Cognitive Science: A Multiple Code Theory. Guilford Press. WRAD dictionary maintained by the DAAP project.",
    url: "https://github.com/DAAP/WRAD",
  },
  {
    id: "epistemic_markers",
    name: "Epistemic & Certainty Markers",
    measures: "Hedging & certainty",
    type: "Automated dictionary",
    body: "An automated scorer counting 106 hedge words (“might”, “somewhat”, “apparent”) and 74 boosters (“clearly”, “definitely”, “must”) per passage, plus a five-level certainty distribution. Heavy hedging with few boosters reads as caution or face-saving; the reverse reads as assertive certainty. On reasoning traces, shifts between the chain of thought and the final output reveal where a model commits versus where it equivocates.",
    authors: "Ken Hyland; Victoria L. Rubin",
    year: "2005 / 2010",
    citation:
      "Hyland, K. (2005). Metadiscourse: Exploring Interaction in Writing. Continuum. Rubin, V. L. (2010). Epistemic modality: From uncertainty to certainty. Information Processing & Management, 46(5), 533–540.",
    url: "https://www.sciencedirect.com/science/article/abs/pii/S0306457310000208",
  },
];
