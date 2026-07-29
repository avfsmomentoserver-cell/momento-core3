---
description: Admin workflow for vocabulary learning system management and feature integration
auto_execution_mode: 3
---

# Admin Workflow

## Overview

The admin workflow provides a structured approach for managing the Momento Core vocabulary learning system, pattern discovery, and feature integration through administrative interfaces. This workflow coordinates the 5 admin components with backend API endpoints and follows the project's skills-first approach.

## Scope

Admin workflow covers:
- Vocabulary learning system management
- Pattern discovery and monitoring
- Feature integration and mapping
- Learning progress tracking
- Vocabulary candidate formalization

## Stages

### 1. Understand Admin Context
- Review current vocabulary system state
- Examine pattern discovery results
- Check feature integration status
- Assess learning progress metrics
- Identify pending candidate evaluations

### 2. Admin Assessment
- Evaluate vocabulary candidates for formalization
- Review pattern discovery effectiveness
- Assess feature integration coverage
- Check learning threshold configuration
- Identify system optimization opportunities

### 3. Execute Admin Operations
- Trigger pattern discovery cycles
- Formalize ready vocabulary candidates
- Import vocabulary as features
- Adjust learning thresholds if needed
- Monitor system health and progress

### 4. Validate Outcomes
- Verify vocabulary formalization success
- Confirm feature integration registration
- Check pattern discovery quality
- Validate learning progress improvements
- Review system performance metrics

### 5. Document Admin Actions
- Log formalization decisions with rationale
- Document pattern discovery results
- Record feature integration changes
- Track learning threshold adjustments
- Update admin workflow documentation

## Admin Components Integration

### Component → API Mapping

| Component | Primary API Endpoints | Purpose |
|-----------|---------------------|---------|
| VocabularyDashboard | `/vocabulary/learning/status`, `/vocabulary/discoveries`, `/vocabulary` | System overview and stats |
| FeatureIntegrationManager | `/vocabulary/features/mapping`, `/vocabulary/features/import`, `/vocabulary/{id}/import-feature` | Feature management |
| LearningProgressTracker | `/vocabulary/learning/progress`, `/vocabulary/learning/auto-formalize` | Progress tracking |
| PatternDiscoveryMonitor | `/vocabulary/discover`, `/vocabulary/discoveries` | Discovery management |
| VocabularyCandidates | `/vocabulary?status=candidate`, `/vocabulary/{id}/evaluate`, `/vocabulary/{id}/formalize` | Candidate management |

## Admin Chat Prompts

### Entry Point Triggers

The admin workflow is activated by the following chat prompt patterns:

- `/admin` - Main admin dashboard entry
- `/admin vocabulary` - Vocabulary system management
- `/admin features` - Feature integration management
- `/admin discovery` - Pattern discovery management
- `/admin learning` - Learning progress management
- `/admin candidates` - Vocabulary candidate management

### Prompt Templates

#### Main Admin Entry
```
/admin
Context: System administration and vocabulary learning management
Goal: Provide admin overview and actionable insights
Scope: Full vocabulary learning system
Expected: System status, key metrics, pending actions
```

#### Vocabulary Management
```
/admin vocabulary
Context: Vocabulary learning system management
Goal: Manage vocabulary entries and formalization process
Scope: Vocabulary candidates, formalized entries, deprecation
Expected: Candidate evaluation, formalization recommendations, system health
```

#### Feature Integration
```
/admin features
Context: Feature integration and mapping management
Goal: Manage vocabulary-to-feature integration
Scope: Feature mapping, import operations, registration status
Expected: Integration status, import recommendations, coverage analysis
```

#### Pattern Discovery
```
/admin discovery
Context: Pattern discovery and monitoring
Goal: Trigger and monitor pattern discovery cycles
Scope: Discovery triggers, results analysis, source-specific discovery
Expected: Discovery results, pattern quality, registration success
```

#### Learning Progress
```
/admin learning
Context: Learning progress tracking and optimization
Goal: Monitor and optimize vocabulary learning progress
Scope: Learning metrics, threshold configuration, auto-formalization
Expected: Progress metrics, threshold analysis, formalization recommendations
```

#### Candidate Management
```
/admin candidates
Context: Vocabulary candidate evaluation and formalization
Goal: Evaluate and formalize vocabulary candidates
Scope: Candidate evaluation, readiness assessment, formalization actions
Expected: Candidate status, evaluation results, formalization decisions
```

## Admin Operations

### Pattern Discovery Operations
- **Trigger All Discovery**: Run discovery across all sources (DNA, Pressure, Moonshot)
- **Source-Specific Discovery**: Run discovery for specific pattern sources
- **Discovery Results Review**: Analyze discovered patterns and registration rates
- **Discovery Quality Assessment**: Evaluate pattern quality and usefulness

### Vocabulary Formalization Operations
- **Candidate Evaluation**: Assess candidates against learning thresholds
- **Individual Formalization**: Formalize specific vocabulary entries
- **Auto-Formalization**: Batch formalize all ready candidates
- **Deprecation Management**: Deprecate outdated or ineffective vocabulary

### Feature Integration Operations
- **Feature Mapping Review**: Assess current vocabulary-to-feature coverage
- **Batch Import**: Import all formalized vocabulary as features
- **Single Import**: Import specific vocabulary entries as features
- **Feature Removal**: Remove outdated or ineffective features

### Learning Optimization Operations
- **Threshold Assessment**: Evaluate current learning threshold effectiveness
- **Threshold Adjustment**: Modify learning parameters if needed
- **Progress Monitoring**: Track learning system improvements over time
- **System Health Check**: Verify overall vocabulary learning system health

## Admin Decision Framework

### Formalization Decision Criteria
- **Usage Count**: Minimum usage threshold met
- **Consistency Score**: Consistent application across analysis
- **Confidence Level**: High average confidence in predictions
- **Time Window**: Recent usage within configured window
- **Semantic Validity**: Clear semantic meaning and utility

### Pattern Integration Criteria
- **Discovery Rate**: Consistent pattern discovery
- **Registration Success**: High pattern-to-vocabulary conversion
- **Prediction Value**: Measurable improvement in forecasts
- **Statistical Significance**: Validated predictive power

### Feature Integration Criteria
- **Formalization Status**: Must be formalized vocabulary
- **Feature Name**: Clear, descriptive feature identifier
- **Registration Success**: Successful feature registry integration
- **API Exposure**: Available through analysis endpoints

## Expected Outputs

### System Status Report
- Vocabulary learning system health metrics
- Pattern discovery effectiveness summary
- Feature integration coverage analysis
- Learning progress improvements
- Pending action recommendations

### Action Recommendations
- Vocabulary candidates ready for formalization
- Pattern discovery opportunities
- Feature integration gaps
- Learning threshold optimization suggestions
- System performance improvements

### Audit Trail
- All formalization decisions with rationale
- Pattern discovery trigger logs
- Feature integration changes
- Learning threshold modifications
- Admin action timestamps and user attribution

## Coordinated By

Project Administrator (ag_admin) with specialist agent support:
- Backend Engineer (ag_backend) for API operations
- Forecast Engineer (ag_forecast) for pattern validation
- Documentation Engineer (ag_docs) for audit trail

## Entry Point Integration

This workflow integrates with the Devin AI entry point system:
- **Entry Point**: `/admin` and sub-commands
- **Skills First**: Automatically uses relevant skills (fastapi, react, momento-core-standards)
- **Agent Coordination**: Project Administrator coordinates specialist agents
- **Fallback Hierarchy**: Skills → Project Admin → Specialist Agents → General Purpose

## Security and Permissions

- All admin operations require operator authentication
- Audit logging for all administrative actions
- User attribution for formalization decisions
- Permission checks via `operator_user` dependency
- Rate limiting on discovery triggers

## Monitoring and Alerts

- Learning progress stagnation alerts
- Pattern discovery failure notifications
- Feature integration error monitoring
- Vocabulary formalization backlog warnings
- System health degradation alerts

## Best Practices

1. **Data-Driven Decisions**: Base formalization on metrics, not intuition
2. **Incremental Changes**: Test threshold adjustments before full deployment
3. **Audit Trail**: Document all admin decisions with rationale
4. **System Health**: Monitor overall system health, not individual metrics
5. **Backward Compatibility**: Ensure changes don't break existing analysis
6. **Testing**: Validate admin operations in development first
7. **Rollback Planning**: Have rollback procedures for major changes

## Integration with Existing Workflows

- **Standard Task**: Use for routine admin operations
- **New Feature**: Use for major vocabulary system enhancements
- **Architecture Review**: Use for vocabulary learning system architecture changes
- **Deployment**: Use for admin interface deployments

## Related Documentation

- `.devin/AGENTS.md` - Agent responsibilities and coordination
- `.devin/CODING_STANDARDS.md` - Coding standards for admin components
- `docs/LINGUISTIC_ADDITIONS_WORKFLOW.md` - Vocabulary addition workflow
- `backend/momento/api/routes/vocabulary.py` - Admin API endpoints
- `web/src/components/admin/` - Admin React components