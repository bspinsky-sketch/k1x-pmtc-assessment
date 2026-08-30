var LEVEL_LABELS = ["None", "Ad-Hoc", "Standardized", "Automated", "Integrated", "Autonomous"];

// Master lookup: capability -> {name, levels:[6 description strings, one per level 0-5]}
// Source: Assessment!G9:L18 ("Description of Selected Level" per level, per capability)
var CURRENT_DESCRIPTIONS = {
  "document_intake": {
    "name": "Document Intake",
    "levels": [
      "No intake process exists. K-1s stay wherever they land, in individual inboxes and on desks, and are retrieved only when someone needs one.",
      "Email or paper delivery",
      "Client uploads to shared folder",
      "Automated collection via client portal",
      "Direct API or system-to-system feed",
      "Digital system-to-system transmission"
    ]
  },
  "inventory_management": {
    "name": "Inventory Management",
    "levels": [
      "No expected-K-1 list exists. Nothing is tracked, so a missing K-1 surfaces only when a return cannot be completed.",
      "No formal tracking or checklist",
      "Manual checklist in spreadsheet",
      "Centralized tracking tool with manual updates",
      "Automated dashboard or alerts tied to workflow system",
      "Comprehensive automated dashboarding across federal, state & international tax"
    ]
  },
  "data_extraction": {
    "name": "Data Extraction",
    "levels": [
      "No data is extracted. The PDF remains the only record, and figures are read off the document each time they are needed.",
      "Manual entry",
      "OCR of federal forms + manual input",
      "AI extraction of full K-1 package",
      "Real-time, event-driven data exchange with continuous validation & reconciliation",
      "Digital system-to-system transmission"
    ]
  },
  "data_validation": {
    "name": "Data Validation",
    "levels": [
      "No validation occurs. Figures are accepted as entered, with nothing checked back to the source K-1.",
      "Manual tick & tie of all data elements based on user knowledge",
      "Manual tick & tie with use of checklists or templates in shared workspace",
      "Automated system validation with some manual tick & tie",
      "Automated system validation with AI-assisted anomaly detection",
      "Digital system-to-system transmission"
    ]
  },
  "data_review": {
    "name": "Data Review",
    "levels": [
      "No review occurs. Whatever the preparer produces moves forward without a second set of eyes or a documented sign-off.",
      "Tick & tie of all data in tax software against source documentation",
      "Use of review checklists & signoff protocols. More than 1 layer of review within shared workspace",
      "Aggregated review of data in bulk with focus on reasonableness and outliers",
      "Aggregated review of data by specialists to surface value-add insights & opportunities",
      "Automated insights and exceptions. Firmwide dashboards of high-risk and prioritization."
    ]
  },
  "tax_analysis_reporting": {
    "name": "Tax Analysis & Reporting",
    "levels": [
      "No analysis occurs. Figures are placed on the return without evaluating or documenting positions, capital accounts, or state and international detail.",
      "Basic compliance only; limited documentation of tax positions.",
      "Ad-hoc analysis with minimal support or tracking.",
      "Documented tax positions and maintained capital accounts; some investment-level analysis.",
      "Formal tax memos and forward-looking analysis of anticipated sales or impacts.",
      "Proactive planning and forecasting integrated into tax strategy."
    ]
  },
  "integration": {
    "name": "Integration",
    "levels": [
      "No data flow exists. Nothing passes between K-1 data and e-file software, and every season is rebuilt from scratch.",
      "Manual keypunching directly into e-file software.",
      "Enter data into Excel or workpapers, then import to e-file software.",
      "Use native integrations from K-1 collection tools.",
      "Custom APIs connect consolidated workpapers to e-file software.",
      "Fully automated digital transmission from source data to e-file software."
    ]
  },
  "resource_structure": {
    "name": "Resource Structure",
    "levels": [
      "No team model exists. K-1 work lands on whoever has capacity that week, with no defined roles, ownership, or handoffs.",
      "Named staff handle K-1 work each season, but with no standard process and limited ability to leverage lower-cost resources.",
      "Defined engagement teams with staff handling input and validation, managers reviewing details.",
      "Staff own full validation; managers review aggregated data for anomalies and trends.",
      "Centralized or pooled team established for consistency and scale.",
      "ITAX and SALT specialists analyze aggregated data to identify consulting opportunities."
    ]
  },
  "advisory": {
    "name": "Advisory",
    "levels": [
      "K-1 data is not retained in usable form. Once the return is filed there is nothing left to query, so no insight or advisory conversation is possible.",
      "K-1 data is used once for filing, then archived; no reuse, reporting, or analytics",
      "Ad-hoc reporting pulled manually from spreadsheets; no standard metrics or portfolio view",
      "Standardized dashboards and portfolio-level reporting drawn from platform data",
      "Internal cross-entity and year-over-year analytics with anomaly detection inform planning and surface advisory opportunities",
      "K-1 data is operated as a strategic asset; K1xInsights peer-cohort benchmarking and predictive analytics drive advisory services and forward-looking decisions"
    ]
  },
  "governance_trust": {
    "name": "Governance & Trust",
    "levels": [
      "No controls exist. K-1 data sits in personal email and local drives. Automation has not been raised internally, and the cost of a single K-1 is unknown.",
      "Data sits in firm systems but controls are informal and IRC 7216 consent is handled ad hoc. Automation has been discussed with no owner. Payoff is assumed, not measured.",
      "Manual sign-offs and checklists govern the work, access is granted case by case. Vendors are being evaluated without a structured plan. Savings are tracked occasionally against no baseline.",
      "Documented controls with role-based access, logged changes, and an IRC 7216 consent framework. Pilots run in select teams. A documented baseline tracks cost-per-K-1, cycle time, and exception rate.",
      "Immutable, timestamped audit trail, segregation of duties enforced at the data level, 7216 controls examination-ready. A funded roadmap scales firm-wide. Realized gains are redeployed and reviewed with leadership.",
      "Continuous, policy-enforced governance with IRS-defensible audit trail and SOC 2 aligned controls. Automation is embedded with change management. Value compounds, benchmarked against peers and reinvested season over season."
    ]
  }
};

// Master lookup: capability -> {name, levels:[6 arrays of advice bullets, one per level 0-5; null at level 5 -- no next step above Autonomous]}
// Source: Data!B68:H80 ("Next Step - Advice to get to next level"), read live via HLOOKUP by Assessment!Q9:Q18
var NEXT_STEP_ADVICE = {
  "document_intake": {
    "name": "Document Intake",
    "levels": [
      [
        "Map every channel K-1s arrive through today: email, mail, portals, fax, and hand-delivery",
        "Designate one central intake point and assign a single owner to monitor it",
        "Start a simple log of what has arrived, what is missing, and what is in process",
        "Set a defined intake window and communicate it to every sender"
      ],
      [
        "Adopt a consistent file naming and folder structure so every K-1 is organized the same way",
        "Make K1Aggregator the single upload destination for all incoming K-1s",
        "Teach senders how to submit correctly: accepted file types, naming, and where to send",
        "Use Batch View and Upload Manager to see what processed, what errored, and what needs attention"
      ],
      [
        "Use the K1x APIs (developers.k1x.io) to automate how K-1s are uploaded and retrieved",
        "Set up automated alerts so the team knows the moment new documents arrive",
        "After each batch, review K-1 Reader results to confirm documents matched correctly",
        "Define processing SLAs by volume and complexity so intake has a measurable standard",
        "Export K1Aggregator upload and processing data to track intake volume over time"
      ],
      [
        "Identify every GP, fund admin, and custodian that could connect directly by API",
        "Use K-1 Reader validation as the first quality check on incoming data, at the point of intake",
        "Standardize how the team triages and resolves Upload Manager error flags",
        "Promote K1xChange digital transmission to any source still sending manually, and track the share of sources connected digitally",
        "Flag K1 Creator-originated K-1s as pre-structured digital data that needs no document processing"
      ],
      [
        "Benchmark intake cycle time against prior years and peer cohorts, and set the next target from it",
        "Drive the .k1x structured file format across your full sender network as the default",
        "Push for digital transmission across 100% of senders so manual document intake approaches zero",
        "Fold every new source into digital intake from day one, so onboarding never reintroduces manual handling"
      ],
      null
    ]
  },
  "inventory_management": {
    "name": "Inventory Management",
    "levels": [
      [
        "Build a list of every expected K-1, by entity, fund, and tax year, using last year as your starting point",
        "Adopt K1Aggregator as the system of record for K-1 inventory, centralizing tracking in one place",
        "Assign a clear owner for completeness, one person responsible per client or entity",
        "Set a reconciliation cadence: weekly during peak season, monthly off-season"
      ],
      [
        "Standardize K1Aggregator organizational features: use tags to categorize investments, and filtering and custom fields to support team workflows",
        "Implement role-based dashboards so engagement leads see their portfolio and managers see cross-engagement status",
        "Track received, missing, and in-process status inside the platform rather than in side spreadsheets",
        "Establish a shared definition of \"complete\" so every owner is measuring inventory the same way"
      ],
      [
        "Create automated alerts for inventory milestones: percentage-received thresholds, aging missing items, and approaching deadlines",
        "Use K1Aggregator Aggregate Investment Review and rollover matching to spot year-over-year changes: new funds, closed positions, and volume shifts",
        "Turn missing-item alerts into a standard follow-up process with senders, not a manual chase",
        "Track aging on outstanding K-1s so the team works the oldest gaps first"
      ],
      [
        "Use tags and filtering to segment inventory by federal, state, and international filing requirements",
        "Use rollover and matching to compare expected inventory against actual receipts, and build a team process for regularly reviewing the gaps",
        "Export K1Aggregator reports to produce client- and stakeholder-facing inventory status updates",
        "Report completeness against deadlines on a set cadence so status is visible before it becomes a problem"
      ],
      [
        "Use inventory data to inform capacity planning, letting volume forecasts guide how you pre-allocate processing resources",
        "Benchmark completeness timing against prior years and set the next target from it",
        "Fold every new entity, fund, or client into the expected-K-1 list from day one, so onboarding never reopens a tracking gap",
        "Feed recurring late or missing sources back into intake, tightening the sender network season over season"
      ],
      null
    ]
  },
  "data_extraction": {
    "name": "Data Extraction",
    "levels": [
      [
        "Run a K1Aggregator proof of concept during onboarding: test AI extraction across a sample of your K-1 complexity levels to see what it handles",
        "Map your current manual process end to end: where time is spent, where errors come from, and where rework happens",
        "Use the K1x ROI calculator (k1x.io/roi) to quantify current manual entry cost, time per K-1 and total processing effort, as your baseline",
        "Identify who can take on validation of AI-extracted data, shifting that work to preparers or junior staff so senior reviewers focus on analysis and exceptions"
      ],
      [
        "Upload K-1s into K1Aggregator to build toward full-volume AI extraction, starting with what you have purchased",
        "Train preparers and junior staff to validate AI-extracted data, moving team effort from manual entry to review and exception handling",
        "Set extraction performance benchmarks, tracking time savings and exception rates against your manual baseline",
        "Identify K-1 types where K-1 Reader extraction is limited (scanned, pre-2018, non-standard formats) and evaluate internal adjustments or K1 Creator structured delivery as an alternative to manual input"
      ],
      [
        "Train manager-level resources to review portfolio-level, aggregated data rather than individual K-1s",
        "Measure time per K-1 at the extraction stage and compare against the Stage 1 pre-automation baseline",
        "Define roles and handoff protocols between preparers validating extracted data and reviewers approving final output",
        "Document SOPs separating K-1s that need manual intervention from those that flow through Reader cleanly"
      ],
      [
        "Establish cross-functional alignment across tax, operations, and technology on the extraction workflow",
        "Build internal SLAs for extraction-to-review turnaround by K-1 complexity tier",
        "Formalize how the team has rebalanced from data entry to exception management and analysis, and staff to that model",
        "Explore K1 Creator as a source of pre-structured data that bypasses extraction entirely for digitally originated K-1s"
      ],
      [
        "Drive adoption of the .k1x structured file format to eliminate the extraction step for digital-native K-1s",
        "Run a sender management program that actively migrates remaining PDF-based sources toward digital transmission",
        "Track the share of volume arriving pre-structured and set the next target from it, so extraction shrinks season over season",
        "Fold every new source into digital-first delivery at onboarding, so growth never reintroduces manual extraction"
      ],
      null
    ]
  },
  "data_validation": {
    "name": "Data Validation",
    "levels": [
      [
        "Create a standardized validation checklist for preparers and junior staff",
        "Assign validation work to staff-level team members with clear escalation paths",
        "Set expected validation time by K-1 complexity level as your baseline to improve against",
        "Log which errors recur so you know where automation will pay off first"
      ],
      [
        "Let K1Aggregator handle automated federal validation and focus your manual checklist on state and international areas",
        "Run year-over-year comparison checks and flag significant variances from prior-year values for review",
        "Create a validation error log to track recurring issues by sender, fund, or K-1 type",
        "Reallocate the time saved on federal checks toward the higher-risk state and international review"
      ],
      [
        "Use K1Aggregator reports and dashboards for exception reviews and delta checks",
        "Configure K1Aggregator validation rules to enforce cross-field consistency automatically",
        "Set up batch validation workflows so the team reviews at the portfolio level rather than K-1 by K-1",
        "Route only flagged exceptions to senior reviewers, so clean records pass without manual touch"
      ],
      [
        "Implement cross-entity validation to detect inconsistencies across related K-1s in the same fund family or investment group",
        "Establish validation SLAs by complexity tier",
        "Explore K1 Creator via the .k1x file type to reduce validation scope for digitally originated data",
        "Track exception rates by source so you know which senders drive the most rework"
      ],
      [
        "Drive adoption of structured .k1x transmission to eliminate validation on digitally sourced K-1s",
        "Use validation exception data to give senders structured feedback, reducing errors at the source",
        "Track the share of volume validated automatically and set the next target from it, so manual validation shrinks season over season",
        "Fold every new source into structured transmission at onboarding, so growth never reintroduces manual validation"
      ],
      null
    ]
  },
  "data_review": {
    "name": "Data Review",
    "levels": [
      [
        "Define the handoff point between validation and review: what must be complete before review starts, and make sure review checklists do not repeat validation steps",
        "Set up clear sign-off protocols for reviewers",
        "Start a review issue log to capture recurring catches, building your team's institutional knowledge over time",
        "Set expected review time by complexity level as your baseline to improve against"
      ],
      [
        "Train managers to review at the portfolio level, on aggregated data rather than K-1 by K-1",
        "Give each review layer a distinct purpose: first pass for correctness, second pass for reasonableness and outliers",
        "Use sampling for high-volume, low-complexity K-1s and reserve full review for exceptions",
        "Feed recurring catches from the issue log back into validation, so review stops re-finding the same errors"
      ],
      [
        "Bring SALT and international tax specialists into K1Aggregator dashboard reviews to surface and document advisory opportunities",
        "Prioritize review by risk, focusing deeper scrutiny where exposure is highest",
        "Make year-over-year variance analysis a standard part of the review process",
        "Document the advisory opportunities review surfaces, not just the corrections it catches"
      ],
      [
        "Use K1Aggregator Executive Summary and Advanced Reporting to surface firm-level risk and consulting opportunities",
        "Use portfolio-level reporting and historical comparison to identify trends across clients and funds",
        "Pull Executive Summary and reporting data to build review summaries for stakeholders",
        "Build a formal feedback loop so specialist review findings reach your advisory and business development teams"
      ],
      [
        "Operate review as a source of advisory leads, routing the opportunities it surfaces to advisory and business development as a standing process",
        "Concentrate review effort on genuine exceptions as validation and extraction mature, so manual review shrinks season over season",
        "Benchmark review turnaround and catch rates against prior years, and set the next target from them",
        "Fold recurring findings into upstream validation rules and templates, so the operation stops re-reviewing what it has already learned"
      ],
      null
    ]
  },
  "tax_analysis_reporting": {
    "name": "Tax Analysis & Reporting",
    "levels": [
      [
        "Start documenting recurring tax issues and build templates so positions are captured consistently",
        "Build a tax position inventory, cataloging known positions, exposures, and elections across the portfolio",
        "Set a standard workpaper format for K-1 tax analysis",
        "Identify where staff-level team members have gaps in tax analysis fundamentals"
      ],
      [
        "Formalize workpapers and build entity-level analysis covering SALT, FTC, Section 199A, and other key provisions",
        "Build analysis templates by entity type: partnership, S-corp, trust, and estate",
        "Set up a way to track tax analysis requests and completions",
        "Build quality review checkpoints into the tax analysis workflow"
      ],
      [
        "Write formal memos for significant tax positions",
        "Model future tax scenarios: anticipated sales, redemptions, or restructuring impacts",
        "Connect tax analysis to specific investment events, linking positions to transactions, distributions, and capital calls",
        "Build reporting templates that translate tax analysis into summaries stakeholders can actually read and use"
      ],
      [
        "Build forecasting models that connect tax strategy to operational planning, using K1Aggregator data as the foundation",
        "Turn tax analysis into advisory deliverables, positioning these insights as value-add services that go beyond compliance",
        "Deliver analysis on a planning calendar throughout the year, not only at filing",
        "Package recurring analyses (SALT exposure, FTC, scenario impacts) into named, repeatable deliverables"
      ],
      [
        "Operate tax analysis as a standard, repeatable service line rather than a per-engagement effort",
        "Feed analysis outputs into K1xInsights benchmarking so positions are read against peer and portfolio context",
        "Benchmark analysis turnaround and advisory attach rate against prior years, and set the next target from it",
        "Tie recurring findings into client planning and re-up conversations, positioning tax analysis as a differentiator",
        "Fold every new entity type or provision into the template library so the capability compounds rather than restarts each season"
      ],
      null
    ]
  },
  "integration": {
    "name": "Integration",
    "levels": [
      [
        "Build standard workpapers that bridge K-1 data to what your e-file software needs as inputs",
        "Train staff on K1Aggregator integrations, walking through which connections are available and how they are configured",
        "Map your current manual keypunching process end to end",
        "Identify every downstream system that receives K-1 data: tax preparation, portfolio management, reporting, and compliance"
      ],
      [
        "Standardize use of K1Aggregator native integrations to feed tax returns",
        "Validate data integrity after integration, confirming outbound data before it reaches the target system",
        "Eliminate intermediate Excel workpapers wherever K1Aggregator feeds the target system directly",
        "Document integration mapping rules: which K-1 fields map to which target-system fields"
      ],
      [
        "Build custom API connections via developers.k1x.io for any system not covered by native integrations",
        "Set up automated validation that runs before imports, catching issues before they reach the target system",
        "Assign a clear internal owner for integration maintenance to monitor, troubleshoot, and update connections",
        "Track integration failures and reprocessing so recurring break points get fixed, not just re-run"
      ],
      [
        "Explore K1xChange for digital transmission of K-1 data files",
        "Map remaining manual data flows and prioritize automation candidates by volume and error frequency",
        "Use K1 Creator-originated .k1x files for direct integration with downstream tax preparation systems, bypassing manual transfer for Creator-sourced K-1s",
        "Extend validated integration to every downstream system identified in Stage 1, not just tax preparation"
      ],
      [
        "Drive adoption of the .k1x file format across the full integration ecosystem, from source through every downstream system",
        "Track the share of data flowing end to end without manual transfer and set the next target from it, so manual handoffs approach zero",
        "Fold every new downstream system or source into validated, automated integration at onboarding, so growth never reintroduces keypunching",
        "Feed integration performance back to sources and system owners, tightening the connected ecosystem season over season"
      ],
      null
    ]
  },
  "resource_structure": {
    "name": "Resource Structure",
    "levels": [
      [
        "Document current process workflows end to end",
        "Define clear role descriptions for each processing step with required skill levels",
        "Train staff-level resources on validation steps using K1Aggregator",
        "Identify the highest-cost activities performed by senior resources that could be delegated"
      ],
      [
        "Give staff full ownership of validation and shift managers to aggregated review",
        "Set up role-based access in K1Aggregator using the Group Management feature so each person sees what they need",
        "Build role-specific onboarding guidance for your team - preparers, managers, and reviewers all ramp differently. Use K1x best practices as a starting point and adapt for how your organization works.",
        "Track cost-per-K-1 by resource level - this is your baseline for measuring efficiency gains over time"
      ],
      [
        "Centralize K-1 operations and standardize how processes run across teams",
        "Balance workload across the resource pool so capacity is used consistently",
        "Make K1xpert Certification part of your team's career development path",
        "Build cross-training rotations for redundancy and flexibility when volume spikes or people are out"
      ],
      [
        "Bring SALT and international tax specialists into the centralized team",
        "Implement productivity metrics by role: processing volume and review turnaround time",
        "Build capacity planning models to anticipate resource needs before busy season hits",
        "Use K1x power-user identification to develop internal champions as peer trainers and first-line support"
      ],
      [
        "Put the specialist team's insights to work, translating what they find in the data into advisory services that go beyond compliance",
        "Scale volume without adding proportional headcount, and track K-1s processed per person as proof of leverage",
        "Reinvest reclaimed senior capacity into the highest-margin advisory work, and measure the shift",
        "Fold every new hire and role into the certified, cross-trained model at onboarding, so growth never rebuilds the team from scratch"
      ],
      null
    ]
  },
  "advisory": {
    "name": "Advisory",
    "levels": [
      [
        "Stop treating the K-1 as a one-time filing input - keep every extracted K-1 in K1Aggregator as a reusable data record, not an archived PDF",
        "Pick two or three questions clients or stakeholders already ask (income by entity, state exposure, year-over-year change) and answer them from K1Aggregator data",
        "Export K1Aggregator data and build a first simple summary view by client, fund, or entity",
        "Use the K-1 Analyzer to review extracted values for outliers and anomalies instead of filing and moving on",
        "Assign one person to own \"what does the data tell us\" as a defined post-filing task, not an afterthought"
      ],
      [
        "Define a standard set of advisory metrics you report every season (income composition, state footprint, foreign activity, allocation shifts) so reporting is consistent client to client",
        "Replace manual spreadsheet pulls with K1Aggregator reports and dashboards as the source of record",
        "Build portfolio-level and entity-level views in K1Aggregator rather than one-off, per-K-1 lookups",
        "Use tags, filtering, and custom fields to segment the portfolio the way your advisory conversations are organized",
        "Standardize one export format so the same report is produced repeatably and shared with clients or stakeholders"
      ],
      [
        "Run year-over-year comparisons in K1Aggregator to flag material changes in income, allocations, and state exposure, and turn each flag into a client conversation",
        "Use cross-entity analysis across related K-1s in the same fund family or investment group to surface inconsistencies and planning opportunities",
        "Use the K-1 Analyzer and K-3 detail to surface foreign income and multi-state exposure that create planning and mitigation opportunities",
        "Build a repeatable process for converting anomalies and red flags into proactive advisory outreach, not just corrections",
        "Capture recurring findings (after-tax ROI, allocation history, tax planning items) so they feed planning rather than disappearing after the filing"
      ],
      [
        "Adopt K1xInsights peer-cohort benchmarking to move from internal comparison to market context clients cannot get anywhere else",
        "Use predictive analytics to shift advisory from backward-looking reporting to forward-looking planning and scenario guidance",
        "Package repeatable outputs (after-tax ROI analysis, fund performance benchmarking, tax planning and mitigation, anomaly detection) into named, billable service lines",
        "Build an advisory calendar that delivers insight throughout the year, not only at filing, so K-1 data drives ongoing engagement",
        "Tie advisory findings to a shared value plan with each client so the value delivered is measured and visible"
      ],
      [
        "Benchmark your advisory revenue and attach rate against peers and prior years, and set growth targets against them",
        "Continuously expand the K1xInsights metric set as new benchmarking and predictive capabilities are released",
        "Feed demand signals back into the practice, using data on what clients ask for to shape new service offerings",
        "Make K-1 data intelligence a standard part of new-client pitches and re-up conversations, positioning the data asset as a differentiator"
      ],
      null
    ]
  },
  "governance_trust": {
    "name": "Governance & Trust",
    "levels": [
      [
        "Get K-1 data out of email and shared drives and into K1Aggregator as the single governed store of record",
        "Document who can see and touch K-1 data, and flag where IRC 7216 exposure exists today",
        "Find the people curious about automation, these are your champions, and write down where processing breaks",
        "Establish your manual baseline with the K1x ROI calculator (k1x.io/roi) to price time and cost per K-1",
        "Name one owner accountable for governance, adoption, and whether the investment returns value"
      ],
      [
        "Move to role-based access in K1Aggregator so each user sees only what their role requires",
        "Rely on the system-captured audit trail as the record of who changed what and when, not manual logs",
        "Define what a successful POC looks like before you start: scope, success metrics, and participant feedback",
        "Set extraction and cycle-time benchmarks against your manual baseline and track them each batch",
        "Convert time saved into a dollar figure using a standard labor rate so value reads in business terms"
      ],
      [
        "Document end-to-end lineage from K-1 receipt to filing so any value can be traced on demand",
        "Make IRC 7216 compliance a design standard for every K-1 workflow, not a case-by-case judgment",
        "Build a formal adoption roadmap with milestones, named owners, and a change management plan",
        "Co-create a value plan with K1xcelerator tying usage to the outcomes you expect before going live",
        "Track realized value against each priority goal, not aggregate hours saved, and review it with leadership"
      ],
      [
        "Extend the audit trail across the ecosystem so lineage holds from GP creation to LP filing",
        "Run a mock audit: prove accuracy, completeness, and lineage using only K1Aggregator reports",
        "Scale K1Aggregator from select teams to firm-wide standard use, closing gaps found in Business Strategy Reviews",
        "Quantify second-order value: penalties avoided, tools retired, capacity added without headcount",
        "Attach realized value to renewal and expansion decisions so investment tracks outcomes"
      ],
      [
        "Treat audit defensibility as a differentiator in re-up and new-fund conversations, not just a control",
        "Benchmark governance maturity against peers and use it as a trust signal in LP diligence",
        "Track adoption depth (certifications, active users, utilization versus benchmark) and set the next target from it",
        "Show value compounding season over season, benchmarked on ROI, break-even, and margin improvement",
        "Feed governance and value evidence into executive and board reporting as proof of fiduciary integrity"
      ],
      null
    ]
  }
};

var KEY_ORDER = ["document_intake", "inventory_management", "data_extraction", "data_validation", "data_review", "tax_analysis_reporting", "integration", "resource_structure", "advisory", "governance_trust"];
