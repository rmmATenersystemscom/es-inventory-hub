# How to Use Domain Analysis Skill with Claude Web

You now have the domain analysis methodology packaged into files you can use with Claude on the web (claude.ai).

## Files Created

1. **`domain-analysis-skill.md`** - Full comprehensive template (12,000+ words)
   - Complete structure with all sections explained
   - Examples for every section
   - Industry-specific customization notes
   - Use this as a reference guide

2. **`domain-analysis-prompt.txt`** - Condensed system prompt (1,500 words)
   - Ready to paste into Claude Projects
   - All the key instructions in compact form
   - Use this for actual implementation

3. **This file** - Instructions for setup

---

## Option 1: Using Claude Projects (Recommended)

Claude Projects allow you to set custom instructions that apply to every conversation in that project.

### Setup Steps:

1. **Go to Claude.ai and create a new Project**
   - Click "Projects" in the sidebar
   - Click "+ New Project"
   - Name it: "Domain Analysis - StoryBrand & AI"

2. **Add Custom Instructions**
   - In the project, click "⚙️ Settings" or "Customize"
   - Find the "Custom Instructions" or "Project Instructions" field
   - Copy the entire contents of `domain-analysis-prompt.txt`
   - Paste into the custom instructions field
   - Save

3. **Add the Full Template as Knowledge**
   - In the same project, look for "Add Knowledge" or "Project Files"
   - Upload `domain-analysis-skill.md` as a knowledge file
   - This gives Claude the full detailed template to reference

4. **Use the Project**
   - Start a new chat within this project
   - Simply type: "Analyze [domain.com] - they are a [industry] business"
   - Claude will follow the complete analysis structure automatically

### Example Usage:

```
You: Analyze qualityplumbingpro.com - plumbing company in Louisiana

Claude: [Performs complete analysis following the template]
```

---

## Option 2: One-Time Prompt (No Project)

If you don't want to use Projects, you can paste the instructions at the start of each conversation.

### Steps:

1. **Start a new conversation with Claude**

2. **Paste this prompt:**

```
[Paste the contents of domain-analysis-prompt.txt here]

Now analyze: [domain.com] - they are a [industry] business in [location]
```

3. **Claude will perform the analysis**

### Drawbacks:
- Have to paste the prompt every time
- Uses more tokens per conversation
- Less convenient than Projects

---

## Option 3: Saved Prompts (Browser Extension/Snippet Tool)

Use a text expander or snippet tool to save the prompt.

### Recommended Tools:
- **Text Blaze** (Chrome extension)
- **Alfred** (Mac)
- **TextExpander**
- **Espanso** (Cross-platform, free)

### Setup:
1. Create a snippet with shortcut like `/analyze`
2. Snippet content = contents of `domain-analysis-prompt.txt` + "Now analyze: "
3. Type `/analyze` in Claude chat
4. Add the domain and industry
5. Submit

---

## What to Expect

When you use this skill, Claude will:

1. ✅ Research the company (using web search if available)
2. ✅ Analyze the website for StoryBrand compliance
3. ✅ Score each of the 7 StoryBrand elements (1-10)
4. ✅ Identify 4-6 target audience personas with detailed pain points
5. ✅ Provide specific messaging recommendations (actual copy, not generic advice)
6. ✅ Analyze AI/SEO optimization opportunities
7. ✅ Create 5-phase implementation plan
8. ✅ Provide ROI calculation framework with examples
9. ✅ Deliver 8,000-12,000 word comprehensive markdown analysis

### Output Format:
- Complete markdown document
- Ready to save as `[company-name]-analysis.md`
- Professionally formatted
- Immediately actionable

---

## Tips for Best Results

### 1. Provide Clear Input

**Good:**
```
Analyze sauciersplumbingllc.com - family-owned plumbing company specializing in natural gas installations in Louisiana
```

**Better:**
```
Analyze sauciersplumbingllc.com
- Industry: Plumbing (residential & commercial)
- Specialization: Natural gas/propane installations
- Location: Holden, Louisiana (Livingston Parish)
- Additional info: Family-owned, brothers Sammy and Butch, 30+ years experience
```

### 2. Let Claude Do the Research

Don't provide too much information upfront. Let Claude:
- Search for company information
- Find reviews and ratings
- Research market demographics
- Discover unique differentiators

This produces more objective analysis.

### 3. Iterate if Needed

If a section needs more depth:
```
Can you expand the natural gas specialization recommendations with more specific content ideas?
```

If you want different ROI scenarios:
```
Can you recalculate the ROI examples for a company with $10K average job value instead?
```

### 4. Request Specific Formats

```
Can you create just the recommended homepage copy from this analysis as a standalone document?
```

```
Can you extract all the recommended CTAs into a separate list?
```

### 5. Ask for Prioritization

```
If this company only has $15K budget and 30 hours to invest in Year 1, what should they prioritize from this plan?
```

---

## Customizing the Skill

You can modify the prompt files to:

### Focus on Specific Industries

Add to the custom instructions:

```
INDUSTRY SPECIALIZATION: Plumbing/HVAC/Home Services

Additional focus areas:
- Emergency service messaging
- Local SEO and Google Business Profile optimization
- Contractor/builder B2B opportunities
- Seasonal content (winter prep, hurricane season, etc.)
```

### Adjust Output Length

```
TARGET LENGTH: 6,000-8,000 words (more concise)
```

or

```
TARGET LENGTH: 12,000-15,000 words (very comprehensive)
```

### Change ROI Framework

```
ROI CALCULATION: Use service industry metrics
- Average job value: $300-$5,000
- Typical conversion rates: 40-60%
- Focus on recurring revenue opportunities
```

### Add Your Specific Needs

```
ADDITIONAL REQUIREMENTS:
- Include social media strategy recommendations
- Add email marketing campaign suggestions
- Provide Google Ads keyword recommendations
```

---

## Troubleshooting

### Issue: Analysis is too generic

**Solution:** Provide more specific company information upfront, or ask Claude to research more thoroughly:
```
Can you do more research on this company's unique differentiators and competitors before completing the analysis?
```

### Issue: Missing sections

**Solution:** The full template is very long. If Claude doesn't complete all sections in one response:
```
Continue with the remaining sections starting from [section name]
```

### Issue: Can't access website

**Solution:** Claude web may not always be able to fetch websites. Provide key information:
```
The website says: [paste key messaging/services]
```

Or ask Claude to rely more on search:
```
Use web search to gather company information instead of fetching the website directly
```

### Issue: ROI numbers seem off

**Solution:** Provide industry-specific context:
```
For this industry, typical average job value is $X and conversion rates are usually Y%. Can you recalculate?
```

---

## Saving and Using the Output

### 1. Copy the Analysis

Once Claude completes the analysis:
- Copy the entire markdown output
- Save to a file: `company-name-analysis.md`

### 2. Share with Client

- Export as PDF (use a markdown to PDF converter)
- Share the markdown file directly
- Copy sections into a presentation

### 3. Use as Implementation Guide

The analysis includes:
- Specific copy recommendations (use verbatim or adapt)
- Phased action plan (assign to team members)
- Content calendar (blog topics, guide titles)
- ROI calculator (fill in actual numbers)

### 4. Track Progress

Use the analysis as a checklist:
- ✅ Homepage rewrite completed
- ✅ Schema markup implemented
- ⏳ Service pages in progress
- ⬜ FAQ page not started

---

## Example Workflow

### Day 1: Analysis
1. Input domain into Claude Project
2. Review the comprehensive analysis
3. Identify top 3-5 priorities

### Week 1: Quick Wins
1. Implement recommended headline
2. Add clear CTAs
3. Optimize Google Business Profile

### Month 1-3: Foundation
1. Rewrite homepage (1,500 words)
2. Create service pages
3. Implement schema markup

### Month 4-6: Authority
1. Write ultimate guides
2. Create FAQ section
3. Launch blog

### Month 7-12: Scale
1. Add interactive tools
2. Publish case studies
3. Guest posting campaign

---

## Questions?

If you have questions about using this skill:

1. **Read the full template** (`domain-analysis-skill.md`) - it has detailed explanations
2. **Check the examples** - Look at the completed analyses (qualityplumbingpro-analysis.md, etc.)
3. **Ask Claude** - In your project, ask: "Can you explain how to [do specific thing] from this analysis?"

---

## Success Metrics

Track these to measure if the skill is working:

**Short-term (30-90 days):**
- ✅ Completed comprehensive analysis
- ✅ Identified actionable quick wins
- ✅ Implemented homepage improvements
- ✅ Website traffic +20-50%

**Medium-term (6 months):**
- ✅ Service pages published
- ✅ Ranking for target keywords
- ✅ Lead generation increasing
- ✅ Website traffic +100-200%

**Long-term (12 months):**
- ✅ AI systems citing the website
- ✅ Dominating local search
- ✅ Consistent lead flow
- ✅ Measurable ROI (5-20x+)

---

**You're now ready to perform world-class domain analyses using Claude on the web!**

Remember: The quality of analysis depends on:
1. ✅ Quality of research (let Claude search thoroughly)
2. ✅ Specificity of recommendations (not generic)
3. ✅ Actionability (client can implement immediately)
4. ✅ Realism of ROI projections (based on actual industry data)

Good luck! 🚀
