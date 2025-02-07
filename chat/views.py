from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rag.services import RAGService
import json
from django.db import connection, DatabaseError, ProgrammingError
from django.core.exceptions import PermissionDenied
import re

rag_service = RAGService()

ALLOWED_TABLES = ['prospects_financialinstitution', 'prospects_deposittrend']
FORBIDDEN_KEYWORDS = ['insert', 'update', 'delete', 'drop', 'truncate', 'alter', 'create']

@ensure_csrf_cookie
def chat_interface(request):
    """
    Render the chat interface
    """
    return render(request, 'chat/index.html')

@csrf_exempt
@require_http_methods(["POST"])
def process_query(request):
    """
    Process a natural language query and return the response
    """
    try:
        data = json.loads(request.body)
        question = data.get('question')
        
        if not question:
            return JsonResponse({
                'error': 'No question provided'
            }, status=400)
        
        # Process the query using RAG service
        response = rag_service.query(question)
        
        return JsonResponse({
            'answer': response['answer'],
            'relevant_documents': response['relevant_documents'],
            'metadata': response['metadata']
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_trends(request):
    """
    Analyze trends based on natural language query
    """
    try:
        data = json.loads(request.body)
        question = data.get('question')
        
        if not question:
            return JsonResponse({
                'error': 'No question provided'
            }, status=400)
        
        # Analyze trends using RAG service
        response = rag_service.analyze_trends(question)
        
        return JsonResponse(response)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def index(request):
    return render(request, 'chat/index.html')

@require_http_methods(["POST"])
def query(request):
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
        
        # Process the question and generate response
        # This is a placeholder - replace with actual processing logic
        answer = f"You asked: {question}"
        relevant_documents = []
        
        return JsonResponse({
            'answer': answer,
            'relevant_documents': relevant_documents
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
def sql_query(request):
    """
    Execute a SQL query with proper security checks and error handling
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
        
        # Validate query
        if not query:
            return JsonResponse({'error': 'Query cannot be empty'}, status=400)
        
        # Convert to lowercase for security checks, but keep original query for execution
        query_lower = query.lower()
        
        # Security checks
        if any(keyword in query_lower for keyword in FORBIDDEN_KEYWORDS):
            raise PermissionDenied('This type of query is not allowed. Only SELECT queries are permitted.')
        
        if not query_lower.startswith('select'):
            raise PermissionDenied('Only SELECT queries are allowed.')
        
        # Check if query only uses allowed tables
        table_pattern = r'from\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, query_lower)
        if not tables:
            return JsonResponse({'error': 'No FROM clause found in query'}, status=400)
        
        if not all(table in ALLOWED_TABLES for table in tables):
            allowed_tables_str = ', '.join(ALLOWED_TABLES)
            raise PermissionDenied(f'You can only query the following tables: {allowed_tables_str}')
        
        # Execute query
        try:
            with connection.cursor() as cursor:
                # Set timeout at connection level if using PostgreSQL
                if connection.vendor == 'postgresql':
                    with connection.cursor() as timeout_cursor:
                        timeout_cursor.execute('SET LOCAL statement_timeout = 10000')
                
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
            
            return JsonResponse({'results': results})
            
        except ProgrammingError as e:
            error_msg = str(e)
            # Clean up error message for better user understanding
            if 'syntax error' in error_msg.lower():
                error_msg = 'Syntax error in SQL query. Please check your query format.'
            return JsonResponse({'error': f'SQL syntax error: {error_msg}'}, status=400)
        except DatabaseError as e:
            error_msg = str(e)
            if 'statement timeout' in error_msg.lower():
                error_msg = 'Query took too long to execute (timeout after 10 seconds)'
            return JsonResponse({'error': f'Database error: {error_msg}'}, status=400)
    
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500) 