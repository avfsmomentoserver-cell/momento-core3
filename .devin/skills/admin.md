# Admin Skill

## Description
Structured workflow for vocabulary learning system administration, pattern discovery management, and feature integration. Provides systematic approach to managing the Momento Core admin components through chat prompts and API operations.

## Related Technologies
- FastAPI (admin API endpoints)
- React (admin components)
- SQLite (vocabulary data storage)
- WebSocket (real-time admin updates)

## Use Cases
- Vocabulary learning system management
- Pattern discovery monitoring and triggering
- Feature integration and mapping
- Learning progress tracking and optimization
- Vocabulary candidate evaluation and formalization
- Admin dashboard operations
- System health monitoring
- Audit trail management

## Primary Agent
Project Administrator (ag_admin) with specialist support:
- Backend Engineer (ag_backend) for API operations
- Forecast Engineer (ag_forecast) for pattern validation
- Documentation Engineer (ag_docs) for audit logging

## Entry Point Configuration
- **Auto-detect**: Enabled for admin-related keywords
- **Chat Prompts**: `/admin`, `/admin vocabulary`, `/admin features`, `/admin discovery`, `/admin learning`, `/admin candidates`
- **Coordinated by**: ag_admin
- **Workflow**: `admin`

## Skill Detection Keywords

### Primary Keywords
- `admin`, `administration`, `administrator`
- `vocabulary`, `linguistics`, `patterns`
- `discovery`, `pattern discovery`
- `features`, `feature integration`
- `learning`, `learning progress`
- `candidates`, `formalization`
- `dashboard`, `admin dashboard`

### Context Keywords
- `vocabulary management`, `pattern management`
- `feature mapping`, `feature integration`
- `learning system`, `learning optimization`
- `candidate evaluation`, `formalization process`
- `pattern discovery`, `discovery cycle`
- `admin operations`, `system administration`

### Action Keywords
- `formalize`, `deprecate`, `import features`
- `trigger discovery`, `run discovery`
- `evaluate candidates`, `assess learning`
- `manage vocabulary`, `administer system`
- `monitor progress`, `check health`

## Admin Components Integration

### Component Mapping
| Component | Purpose | API Endpoints | Chat Prompts |
|-----------|---------|---------------|--------------|
| VocabularyDashboard | System overview and stats | `/vocabulary/learning/status`, `/vocabulary/discoveries`, `/vocabulary` | `/admin`, `/admin vocabulary` |
| FeatureIntegrationManager | Feature management | `/vocabulary/features/*` | `/admin features` |
| LearningProgressTracker | Progress tracking | `/vocabulary/learning/*` | `/admin learning` |
| PatternDiscoveryMonitor | Discovery management | `/vocabulary/discover`, `/vocabulary/discoveries` | `/admin discovery` |
| VocabularyCandidates | Candidate management | `/vocabulary?status=candidate`, `/vocabulary/{id}/*` | `/admin candidates` |

## Workflow Stages

### 1. Understand Admin Context
- Review current vocabulary system state
- Examine pattern discovery results
- Check feature integration status
- Assess learning progress metrics
- Identify pending candidate evaluations

**API Calls**:
- `GET /api/v1/vocabulary/learning/status`
- `GET /api/v1/vocabulary/discoveries`
- `GET /api/v1/vocabulary/features/mapping`
- `GET /api/v1/vocabulary/learning/progress`

### 2. Admin Assessment
- Evaluate vocabulary candidates for formalization
- Review pattern discovery effectiveness
- Assess feature integration coverage
- Check learning threshold configuration
- Identify system optimization opportunities

**API Calls**:
- `GET /api/v1/vocabulary?status=candidate`
- `POST /api/v1/vocabulary/{id}/evaluate`
- `GET /api/v1/vocabulary/features/mapping`

### 3. Execute Admin Operations
- Trigger pattern discovery cycles
- Formalize ready vocabulary candidates
- Import vocabulary as features
- Adjust learning thresholds if needed
- Monitor system health and progress

**API Calls**:
- `POST /api/v1/vocabulary/discover`
- `POST /api/v1/vocabulary/{id}/formalize`
- `POST /api/v1/vocabulary/learning/auto-formalize`
- `POST /api/v1/vocabulary/features/import`
- `POST /api/v1/vocabulary/{id}/import-feature`

### 4. Validate Outcomes
- Verify vocabulary formalization success
- Confirm feature integration registration
- Check pattern discovery quality
- Validate learning progress improvements
- Review system performance metrics

**API Calls**:
- `GET /api/v1/vocabulary/learning/status`
- `GET /api/v1/vocabulary/features/mapping`
- `GET /api/v1/vocabulary/discoveries`

### 5. Document Admin Actions
- Log formalization decisions with rationale
- Document pattern discovery results
- Record feature integration changes
- Track learning threshold adjustments
- Update admin workflow documentation

**Documentation Updates**:
- Audit trail via `db.log_audit()`
- Admin workflow documentation
- System health reports

## API Endpoint Reference

### Vocabulary Management
- `GET /api/v1/vocabulary` - List all vocabulary entries
- `GET /api/v1/vocabulary/{id}` - Get specific vocabulary entry
- `POST /api/v1/vocabulary` - Create vocabulary entry (operator only)
- `PUT /api/v1/vocabulary/{id}/formalize` - Promote candidate to formalized
- `POST /api/v1/vocabulary/{id}/deprecate` - Deprecate vocabulary entry

### Learning System
- `GET /api/v1/vocabulary/learning/status` - Learning system status
- `GET /api/v1/vocabulary/learning/progress` - Learning progress details
- `POST /api/v1/vocabulary/learning/auto-formalize` - Auto-formalize ready candidates
- `POST /api/v1/vocabulary/{id}/evaluate` - Evaluate vocabulary candidate

### Pattern Discovery
- `POST /api/v1/vocabulary/discover` - Trigger pattern discovery
- `GET /api/v1/vocabulary/discoveries` - List pattern discoveries

### Feature Integration
- `GET /api/v1/vocabulary/features/mapping` - Get vocabulary to feature mapping
- `POST /api/v1/vocabulary/features/import` - Import all formalized vocabulary as features
- `POST /api/v1/vocabulary/{id}/import-feature` - Import single vocabulary as feature
- `DELETE /api/v1/vocabulary/{id}/feature` - Remove vocabulary feature

## Admin Decision Framework

### Formalization Decision Criteria
- **Usage Count**: Minimum usage threshold met (default: 10 uses)
- **Consistency Score**: Consistent application across analysis (default: 0.7)
- **Confidence Level**: High average confidence in predictions (default: 0.6)
- **Time Window**: Recent usage within configured window (default: 30 days)
- **Semantic Validity**: Clear semantic meaning and utility

### Pattern Integration Criteria
- **Discovery Rate**: Consistent pattern discovery (>50% success)
- **Registration Success**: High pattern-to-vocabulary conversion (>40%)
- **Prediction Value**: Measurable improvement in forecasts (>5% baseline)
- **Statistical Significance**: Validated predictive power (p < 0.05)

### Feature Integration Criteria
- **Formalization Status**: Must be formalized vocabulary
- **Feature Name**: Clear, descriptive feature identifier
- **Registration Success**: Successful feature registry integration
- **API Exposure**: Available through analysis endpoints

## Security and Permissions

### Authentication Requirements
- All admin operations require operator authentication
- User attribution is logged for all admin actions
- Permission checks via `operator_user` dependency

### Audit Trail
- Every admin action is logged with timestamp and user
- Formalization decisions include rationale and metrics
- System changes are tracked with before/after states
- Audit logs available through admin endpoints

### Rate Limiting
- Pattern discovery triggers are rate-limited (1 per minute)
- Batch operations have size limits (max 100 per operation)
- Threshold adjustments require confirmation
- Critical actions may require multi-step verification

## Monitoring and Alerts

### System Health Metrics
- Vocabulary learning progress trends
- Pattern discovery registration rates
- Feature integration coverage percentage
- Candidate evaluation backlog size
- System performance indicators

### Automated Alerts
- Learning progress stagnation (>7 days without improvement)
- Pattern discovery failure rate >20%
- Feature integration error rate >10%
- Vocabulary formalization backlog >20 candidates
- System health degradation (>15% metric decline)

## Best Practices

### Admin Operations
1. **Data-Driven Decisions**: Base formalization on metrics, not intuition
2. **Incremental Changes**: Test threshold adjustments before full deployment
3. **Audit Trail**: Document all admin decisions with rationale
4. **System Health**: Monitor overall system health, not individual metrics
5. **Backward Compatibility**: Ensure changes don't break existing analysis

### Prompt Usage
1. **Be Specific**: Use specific admin commands for clear operations
2. **Provide Context**: Include relevant background for complex requests
3. **Specify Scope**: Define the scope of admin operations clearly
4. **Request Rationale**: Ask for reasoning behind recommendations

### Error Handling
1. **Check Error Context**: Review impact assessment in error responses
2. **Follow Recommendations**: Adhere to suggested resolution steps
3. **Specialist Assignment**: Accept specialist agent assignments for complex issues
4. **System Recovery**: Allow system recovery time after major operations

## Integration with Existing Skills

### Complementary Skills
- **fastapi skill**: For API endpoint operations and backend integration
- **react skill**: For admin component interactions and UI operations
- **momento-core-standards skill**: For compliance with project standards
- **docs skill**: For audit trail documentation and admin documentation
- **testing skill**: For validating admin operations and system health

### Skill Coordination
The admin skill automatically coordinates with other skills based on the operation context:
- API operations → fastapi skill
- UI component updates → react skill
- Standards compliance → momento-core-standards skill
- Documentation updates → docs skill
- Testing and validation → testing skill

## Related Documentation

- `.devin/workflows/admin.md` - Complete admin workflow specification
- `.devin/ADMIN_PROMPTS.md` - Admin chat prompt specification
- `.devin/config.json` - Devin AI configuration with admin entry points
- `.devin/AGENTS.md` - Agent responsibilities and coordination
- `docs/LINGUISTIC_ADDITIONS_WORKFLOW.md` - Vocabulary addition workflow
- `backend/momento/api/routes/vocabulary.py` - Admin API endpoints
- `web/src/components/admin/` - Admin React component implementations

## Example Usage

### Basic Admin Check
```
User: Check the admin dashboard status
System: [Invokes admin skill, provides system overview]
```

### Vocabulary Management
```
User: Show vocabulary candidates ready for formalization
System: [Invokes admin skill, evaluates candidates, shows recommendations]
```

### Pattern Discovery
```
User: Trigger pattern discovery for all sources
System: [Invokes admin skill, triggers discovery, monitors results]
```

### Feature Integration
```
User: Import all formalized vocabulary as features
System: [Invokes admin skill, executes import, reports results]
```

## Troubleshooting

### Common Issues

#### Admin Commands Not Recognized
- **Cause**: Skill auto-detection not triggered
- **Solution**: Use explicit `/admin` prompt or include admin keywords

#### API Operations Failing
- **Cause**: Authentication or permission issues
- **Solution**: Verify operator authentication and check API permissions

#### Pattern Discovery Not Triggering
- **Cause**: Rate limiting or system health issues
- **Solution**: Check rate limits, verify system health, retry after cooldown

#### Feature Integration Failing
- **Cause**: Vocabulary not formalized or feature name conflicts
- **Solution**: Verify vocabulary formalization status, check for naming conflicts

#### Learning Progress Stalled
- **Cause**: Thresholds too strict or lack of candidate data
- **Solution**: Analyze threshold effectiveness, adjust if needed, ensure data flow

## Future Enhancements

### Planned Skill Features
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