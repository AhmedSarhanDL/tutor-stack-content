# GCS Curriculum Integration

This document describes the new Google Cloud Storage (GCS) integration for dynamically fetching curriculum content.

## Overview

The content service now supports fetching curriculum data from Google Cloud Storage, allowing for dynamic access to curriculum content organized by grade, term, and subject.

## GCS Bucket Structure

The expected GCS bucket structure follows this pattern:

```
thoth-concepts/
└── concepts/
    └── content/
        ├── G10/
        │   ├── Term1/
        │   │   ├── arabic/
        │   │   ├── biology/
        │   │   ├── chemistry/
        │   │   ├── english/
        │   │   ├── geography/
        │   │   ├── history/
        │   │   ├── mathematics/
        │   │   ├── philosophy/
        │   │   └── physics/
        │   └── Term2/
        │       ├── arabic/
        │       ├── biology/
        │       ├── chemistry/
        │       ├── english/
        │       ├── geography/
        │       ├── history/
        │       ├── mathematics/
        │       ├── philosophy/
        │       └── physics/
        ├── G11/
        ├── G12/
        ├── G7/
        ├── G8/
        ├── G9/
        ├── KG1/
        ├── KG2/
        ├── P1/
        ├── P2/
        ├── P3/
        ├── P4/
        ├── P5/
        └── P6/
```

## New API Endpoints

### 1. Get Available Grades
```
GET /content/curriculum/grades
```
Returns a list of all available grades in the GCS bucket.

### 2. Get Grade Structure
```
GET /content/curriculum/structure/{grade}
```
Returns the structure of a specific grade, including terms and subjects.

### 3. Get Grade Curriculum
```
GET /content/curriculum/{grade}
```
Returns the complete curriculum for a specific grade.

### 4. Get Subject Concepts
```
GET /content/curriculum/{grade}/{term}/{subject}
```
Returns concepts for a specific subject within a grade and term.

### 5. Get Concept by Path
```
GET /content/curriculum/{grade}/{term}/{subject}/{concept_name}
```
Returns a specific concept by its full path.

### 6. Get User Curriculum (Enhanced)
```
GET /content/curriculum/user
```
Returns curriculum for the current user's grade, with automatic grade mapping.

## Grade Mapping

The system automatically maps user grades to GCS grade formats:

- User grade "5" → GCS grade "P5"
- User grade "6" → GCS grade "P6"
- User grade "7" → GCS grade "G7"
- User grade "8" → GCS grade "G8"
- User grade "9" → GCS grade "G9"
- User grade "10" → GCS grade "G10"
- User grade "11" → GCS grade "G11"
- User grade "12" → GCS grade "G12"

## Frontend Enhancements

The Curriculum Viewer has been enhanced with:

1. **Grade Selection**: Dropdown to select different grades
2. **Term Filtering**: Filter concepts by term (Term1, Term2)
3. **Subject Filtering**: Filter concepts by subject
4. **Metadata Tags**: Display term and subject tags on concept cards
5. **Enhanced Search**: Search across all concepts with filters applied

## Fallback Mechanism

If GCS is not available or fails, the system falls back to local JSON files:

- P5.json for grade 5
- P6.json for grade 6
- Default to P5.json for other grades

## Configuration

### GCS Authentication

To use GCS integration, you need to set up authentication:

1. **Service Account Key** (Recommended for production):
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

2. **Application Default Credentials** (Development):
   ```bash
   gcloud auth application-default login
   ```

### Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file
- `GCS_BUCKET_NAME`: GCS bucket name (defaults to "thoth-concepts")

## Testing

Run the GCS integration test:

```bash
cd services/content
source ../../venv/bin/activate
python test_gcs_integration.py
```

## Error Handling

The system includes comprehensive error handling:

1. **GCS Connection Errors**: Falls back to local files
2. **Authentication Errors**: Logs error and falls back
3. **Missing Files**: Returns 404 with descriptive message
4. **Invalid JSON**: Logs warning and skips file

## Performance Considerations

1. **Caching**: Consider implementing Redis caching for frequently accessed data
2. **Pagination**: For large datasets, implement pagination
3. **CDN**: Consider using Cloud CDN for static content
4. **Compression**: Enable GCS compression for JSON files

## Security

1. **IAM Roles**: Use least privilege principle for GCS access
2. **Service Account**: Use dedicated service account for the application
3. **Audit Logging**: Enable GCS audit logging
4. **Encryption**: Ensure data is encrypted at rest and in transit

## Monitoring

Monitor the following metrics:

1. **GCS API Calls**: Track request volume and latency
2. **Error Rates**: Monitor authentication and access errors
3. **Cache Hit Rates**: If caching is implemented
4. **Response Times**: Track API response times

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify service account key is valid
   - Check IAM permissions
   - Ensure GOOGLE_APPLICATION_CREDENTIALS is set

2. **Bucket Access Errors**:
   - Verify bucket name is correct
   - Check bucket permissions
   - Ensure bucket exists

3. **File Not Found**:
   - Verify file path structure
   - Check file permissions
   - Ensure files are uploaded to correct location

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.getLogger('tutor_stack_content.gcs_curriculum').setLevel(logging.DEBUG)
``` 