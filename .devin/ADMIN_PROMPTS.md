# Admin Chat Prompts Specification

This document defines the admin chat prompt system for the Momento Core vocabulary learning administration workflow.

## Overview

The admin chat prompt system provides structured commands for managing the vocabulary learning system through natural language interfaces. It integrates with the Devin AI entry point system to route admin commands to the appropriate workflow and specialist agents.

## Entry Point Commands

### Main Admin Commands

#### `/admin` - Main Admin Dashboard
**Purpose**: Access the main admin dashboard for vocabulary learning system overview

**Example Usage**:
```
/admin
```

**Expected Response**:
- System health overview
- Vocabulary learning statistics
- Pattern discovery status
- Feature integration coverage
- Pending action recommendations
- Key metrics and alerts

**Workflow Stage**: Understand Admin Context

**Specialist Agents**: ag_admin (coordinator), ag_backend (API data), ag_forecast (pattern analysis)

---

#### `/admin vocabulary` - Vocabulary Management
**Purpose**: Manage vocabulary entries, candidates, and formalization process

**Example Usage**:
```
/admin vocabulary
Show me vocabulary candidates ready for formalization
```

**Expected Response**:
- Current vocabulary statistics (candidates, formalized, deprecated, total)
- Candidates ready for formalization with evaluation details
- Formalization recommendations
- Learning threshold configuration
- Recent vocabulary changes

**Workflow Stage**: Admin Assessment → Execute Admin Operations

**Specialist Agents**: ag_admin (coordinator), ag_backend (API operations), ag_docs (audit logging)

**Sub-commands**:
- `show candidates` - Display vocabulary candidates
- `evaluate candidates` - Run candidate evaluation
- `formalize <id>` - Formalize specific candidate
- `auto-formalize` - Batch formalize ready candidates
- `deprecate <id>` - Deprecate vocabulary entry

---

#### `/admin features` - Feature Integration Management
**Purpose**: Manage vocabulary-to-feature integration and mapping

**Example Usage**:
```
/admin features
Show feature integration status and import recommendations
```

**Expected Response**:
- Current feature mapping status
- Vocabulary-to-feature coverage analysis
- Registration status by vocabulary
- Import recommendations
- Integration gaps and opportunities

**Workflow Stage**: Admin Assessment → Execute Admin Operations

**Specialist Agents**: ag_admin (coordinator), ag_backend (API operations), ag_forecast (feature validation)

**Sub-commands**:
- `show mapping` - Display vocabulary-to-feature mapping
- `import all` - Import all formalized vocabulary as features
- `import <id>` - Import specific vocabulary as feature
- `remove <id>` - Remove vocabulary feature
- `coverage report` - Generate feature coverage analysis

---

#### `/admin discovery` - Pattern Discovery Management
**Purpose**: Trigger and monitor pattern discovery cycles

**Example Usage**:
```
/admin discovery
Trigger pattern discovery for all sources
```

**Expected Response**:
- Pattern discovery trigger confirmation
- Discovery results (patterns found, registered)
- Recent discovery history
- Source-specific discovery status
- Pattern quality assessment

**Workflow Stage**: Execute Admin Operations → Validate Outcomes

**Specialist Agents**: ag_admin (coordinator), ag_forecast (pattern analysis), ag_backend (API operations)

**Sub-commands**:
- `trigger all` - Run discovery across all sources
- `trigger dna` - Run DNA pattern discovery
- `trigger pressure` - Run pressure pattern discovery
- `trigger moonshot` - Run moonshot pattern discovery
- `show results` - Display recent discovery results
- `quality check` - Assess pattern discovery quality

---

#### `/admin learning` - Learning Progress Management
**Purpose**: Monitor and optimize vocabulary learning progress

**Example Usage**:
```
/admin learning
Show learning progress and threshold analysis
```

**Expected Response**:
- Learning progress metrics (candidates, ready, formalized, total)
- Learning threshold configuration and effectiveness
- Auto-formalization recommendations
- Progress trends over time
- System health indicators

**Workflow Stage**: Admin Assessment → Execute Admin Operations

**Specialist Agents**: ag_admin (coordinator), ag_forecast (learning optimization), ag_backend (API operations)

**Sub-commands**:
- `show progress` - Display learning progress metrics
- `threshold analysis` - Analyze current threshold effectiveness
- `auto-formalize` - Formalize all ready candidates
- `adjust thresholds` - Modify learning parameters
- `health check` - Verify learning system health

---

#### `/admin candidates` - Vocabulary Candidate Management
**Purpose**: Evaluate and manage vocabulary candidates for formalization

**Example Usage**:
```
/admin candidates
Evaluate all vocabulary candidates and show formalization recommendations
```

**Expected Response**:
- Candidate list with evaluation status
- Readiness assessment for each candidate
- Evaluation metrics (usage, consistency, confidence)
- Formalization recommendations with rationale
- Auto-formalization eligibility

**Workflow Stage**: Admin Assessment → Execute Admin Operations

**Specialist Agents**: ag_admin (coordinator), ag_forecast (candidate evaluation), ag_backend (API operations)

**Sub-commands**:
- `list candidates` - Show all vocabulary candidates
- `evaluate <id>` - Evaluate specific candidate
- `evaluate all` - Evaluate all candidates
- `formalize <id>` - Formalize specific candidate
- `show ready` - Show only ready candidates

## Prompt Patterns

### Status Queries
```
/admin [component] status
/admin [component] health
/admin [component] metrics
```

### Action Commands
```
/admin [component] trigger [action]
/admin [component] execute [operation]
/admin [component] run [process]
```

### Evaluation Commands
```
/admin [component] evaluate [target]
/admin [component] assess [subject]
/admin [component] analyze [aspect]
```

### Management Commands
```
/admin [component] manage [resource]
/admin [component] configure [setting]
/admin [component] optimize [parameter]
```

## Contextual Prompts

### Problem-Solving Prompts
```
/admin vocabulary
We have 50 candidates stuck in evaluation. Investigate and recommend actions.
```

### Optimization Prompts
```
/admin learning
Learning progress has stalled. Analyze thresholds and suggest improvements.
```

### Investigation Prompts
```
/admin discovery
Pattern discovery registration rate dropped to 40%. Investigate causes.
```

### Reporting Prompts
```
/admin features
Generate a feature integration coverage report with recommendations.
```

## Expected Response Structure

### Standard Response Format
```markdown
## Admin Response: [Component Name]

### System Status
[Current status metrics and health indicators]

### Key Findings
[Important discoveries and analysis results]

### Recommendations
[Actionable recommendations with priorities]

### Pending Actions
[Items requiring admin attention]

### Audit Trail
[Recent admin actions and changes]
```

### Error Response Format
```markdown
## Admin Error: [Component Name]

### Issue Description
[Clear description of the error or problem]

### Impact Assessment
[How this affects the system]

### Recommended Actions
[Steps to resolve the issue]

### Specialist Agent Assignment
[Which specialist agent should handle this]
```

## Integration with Devin AI Configuration

### Entry Point Resolution
1. User enters admin command (e.g., `/admin vocabulary`)
2. Devin AI config matches command to entry point trigger
3. Routes to admin workflow with appropriate context
4. Project Administrator coordinates specialist agents
5. Skills-first approach applies relevant skills automatically

### Skill Auto-Detection
Based on the admin command context, the system automatically invokes:
- **fastapi skill**: For API endpoint operations
- **react skill**: For admin component interactions
- **momento-core-standards skill**: For compliance with project standards
- **docs skill**: For audit trail documentation

### Agent Coordination
- **Project Administrator (ag_admin)**: Primary coordinator for all admin operations
- **Backend Engineer (ag_backend)**: API operations and database interactions
- **Forecast Engineer (ag_forecast)**: Pattern validation and learning optimization
- **Documentation Engineer (ag_docs)**: Audit trail and admin documentation

## Usage Examples

### Example 1: Daily Admin Check
```
User: /admin
System: [Provides system overview, shows 3 candidates ready for formalization, 
        pattern discovery running at 85% registration rate]

User: /admin candidates auto-formalize
System: [Formalizes 3 ready candidates, updates audit trail, 
        shows new learning progress metrics]
```

### Example 2: Investigation
```
User: /admin discovery
System: [Shows discovery status, recent registration rate drop to 40%]

User: /admin discovery quality check
System: [Analyzes pattern quality, identifies moonshot discovery issues, 
        recommends source-specific investigation]

User: /admin discovery trigger moonshot
System: [Triggers moonshot-specific discovery, monitors results, 
        reports improved registration rate]
```

### Example 3: Feature Integration
```
User: /admin features coverage report
System: [Shows 65% feature coverage, identifies gaps in pressure patterns]

User: /admin features import all
System: [Imports 12 formalized vocabulary as features, 
        updates coverage to 78%, logs audit trail]
```

## Best Practices

### Prompt Composition
1. **Be Specific**: Use specific sub-commands rather than generic requests
2. **Provide Context**: Include relevant background information for complex requests
3. **Specify Scope**: Define the scope of admin operations clearly
4. **Request Rationale**: Ask for reasoning behind recommendations

### Response Interpretation
1. **Review System Status**: Always check system health first
2. **Prioritize Recommendations**: Focus on high-priority action items
3. **Verify Audit Trail**: Ensure all actions are properly logged
4. **Validate Outcomes**: Confirm expected results were achieved

### Error Handling
1. **Check Error Context**: Review impact assessment in error responses
2. **Follow Recommendations**: Adhere to suggested resolution steps
3. **Specialist Assignment**: Accept specialist agent assignments for complex issues
4. **System Recovery**: Allow system recovery time after major operations

## Security and Permissions

### Authentication Requirements
- All admin commands require operator authentication
- User attribution is logged for all admin actions
- Permission checks are performed via `operator_user` dependency

### Audit Trail
- Every admin action is logged with timestamp and user
- Formalization decisions include rationale and metrics
- System changes are tracked with before/after states
- Audit logs are available through admin endpoints

### Rate Limiting
- Pattern discovery triggers are rate-limited
- Batch operations have size limits
- Threshold adjustments require confirmation
- Critical actions may require multi-step verification

## Monitoring and Alerts

### Automated Alerts
- Learning progress stagnation (>7 days without improvement)
- Pattern discovery failure rate >20%
- Feature integration error rate >10%
- Vocabulary formalization backlog >20 candidates
- System health degradation (>15% metric decline)

### Alert Response Prompts
```
/admin learning
Respond to learning progress stagnation alert
```

## Integration with Admin Components

### Component → Prompt Mapping
- **VocabularyDashboard** → `/admin` (overview), `/admin vocabulary` (detailed)
- **FeatureIntegrationManager** → `/admin features`
- **LearningProgressTracker** → `/admin learning`
- **PatternDiscoveryMonitor** → `/admin discovery`
- **VocabularyCandidates** → `/admin candidates`

### API Endpoint Usage
Each admin prompt triggers specific API endpoints as defined in the admin workflow document:
- Pattern discovery prompts → `/vocabulary/discover` endpoints
- Feature integration prompts → `/vocabulary/features/*` endpoints
- Learning prompts → `/vocabulary/learning/*` endpoints
- Candidate prompts → `/vocabulary?status=candidate` and evaluation endpoints

## Future Enhancements

### Planned Prompt Features
- Natural language processing for complex admin requests
- Predictive admin suggestions based on system state
- Automated admin operation scheduling
- Multi-step admin workflow orchestration
- Admin command history and replay

### Integration Opportunities
- Real-time admin notifications via WebSocket
- Admin mobile interface support
- Admin API for external tool integration
- Scheduled admin task automation
- Admin collaboration features

## Related Documentation

- `.devin/workflows/admin.md` - Complete admin workflow specification
- `.devin/config.json` - Devin AI configuration with entry points
- `.devin/AGENTS.md` - Agent responsibilities and coordination
- `backend/momento/api/routes/vocabulary.py` - Admin API endpoints
- `web/src/components/admin/` - Admin React component implementations