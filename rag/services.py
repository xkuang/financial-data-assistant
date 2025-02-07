import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from langchain import PromptTemplate, LLMChain
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from django.conf import settings
from prospects.models import FinancialInstitution, QuarterlyStats
from langchain.schema import Document

class RAGService:
    """
    Service for handling natural language queries about financial institutions
    using Retrieval Augmented Generation (RAG)
    """
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        self.vector_store = None
        self.initialize_vector_store()
    
    def initialize_vector_store(self):
        """
        Initialize or load the vector store with financial institution data
        """
        vector_store_path = os.path.join(settings.BASE_DIR, 'rag_kb', 'vector_store')
        
        if os.path.exists(vector_store_path):
            self.vector_store = FAISS.load_local(vector_store_path, self.embeddings)
        else:
            # Create documents from financial institution data
            documents = self._create_documents()
            
            # Create vector store
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            
            # Save vector store
            os.makedirs(os.path.dirname(vector_store_path), exist_ok=True)
            self.vector_store.save_local(vector_store_path)
    
    def _create_documents(self) -> List[Document]:
        """
        Create documents from financial institution data for vector store
        """
        documents = []
        
        # Get all institutions with their latest stats
        institutions = FinancialInstitution.objects.all().prefetch_related(
            'quarterly_stats'
        )
        
        for inst in institutions:
            latest_stats = inst.quarterly_stats.first()
            if latest_stats:
                # Format currency values
                assets = "${:,.2f}".format(float(latest_stats.total_assets))
                deposits = "${:,.2f}".format(float(latest_stats.total_deposits))
                
                content = f"""
                Institution: {inst.get_institution_type_display()}
                Name: {inst.charter_number}
                Location: {inst.city}, {inst.state}
                Asset Tier: {inst.asset_tier}
                Total Assets: {assets}
                Total Deposits: {deposits}
                Last Updated: {latest_stats.quarter_end_date.strftime('%Y-%m-%d')}
                """
                metadata = {
                    'id': inst.id,
                    'type': inst.institution_type,
                    'charter_number': inst.charter_number,
                    'asset_tier': inst.asset_tier,
                    'state': inst.state,
                    'total_assets': float(latest_stats.total_assets),
                    'total_deposits': float(latest_stats.total_deposits)
                }
                doc = Document(page_content=content.strip(), metadata=metadata)
                documents.append(doc)
        
        return documents
    
    def update_vector_store(self):
        """
        Update the vector store with new or changed data
        """
        # Re-initialize vector store with fresh data
        vector_store_path = os.path.join(settings.BASE_DIR, 'rag_kb', 'vector_store')
        if os.path.exists(vector_store_path):
            os.remove(vector_store_path)
        
        self.initialize_vector_store()
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language query about financial institutions
        """
        # Search for relevant documents
        docs = self.vector_store.similarity_search(question, k=5)
        
        # Create context from relevant documents
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Process different types of questions
        question_lower = question.lower()
        
        if "asset tier" in question_lower:
            from prospects.models import FinancialInstitution
            from django.db.models import Count
            
            stats = FinancialInstitution.objects.values('asset_tier').annotate(
                count=Count('id')
            ).order_by('asset_tier')
            
            total = sum(stat['count'] for stat in stats)
            response = "Here's the breakdown of institutions by asset tier:\n\n"
            for stat in stats:
                percentage = (stat['count'] / total) * 100
                response += f"• {stat['asset_tier']}: {stat['count']:,} institutions ({percentage:.1f}%)\n"
                
        elif any(word in question_lower for word in ["california", "state"]):
            filtered_docs = [
                doc for doc in docs 
                if doc.metadata['state'] == 'CA'
            ]
            
            if filtered_docs:
                response = "Here are some financial institutions in California:\n\n"
                for doc in filtered_docs[:3]:
                    response += doc.page_content.strip() + "\n\n"
            else:
                response = "I couldn't find any institutions matching your criteria in California."
                
        elif "deposit" in question_lower and "decline" in question_lower:
            from django.db.models import F
            from prospects.models import QuarterlyStats
            
            significant_changes = QuarterlyStats.objects.filter(
                deposit_change_pct__lt=-5  # More than 5% decline
            ).select_related('institution').order_by('deposit_change_pct')[:5]
            
            if significant_changes:
                response = "Here are institutions with significant deposit declines:\n\n"
                for stat in significant_changes:
                    inst = stat.institution
                    response += f"• {inst.charter_number} ({inst.city}, {inst.state}): {stat.deposit_change_pct:.1f}% decline\n"
                    response += f"  Current deposits: ${float(stat.total_deposits):,.2f}\n"
            else:
                response = "I couldn't find any institutions with significant deposit declines in the current data."
                
        elif "asset" in question_lower and any(x in question_lower for x in ["over", "above", "more than", ">", "greater"]):
            # Extract the threshold from the question (default to $1B if not found)
            import re
            threshold = 1_000_000_000  # Default $1B
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*[Bb]illion', question)
            if amount_match:
                threshold = float(amount_match.group(1)) * 1_000_000_000
            
            filtered_docs = [
                doc for doc in docs 
                if doc.metadata['total_assets'] > threshold
            ]
            
            if filtered_docs:
                response = f"Here are institutions with assets over ${threshold/1_000_000_000:.1f}B:\n\n"
                for doc in filtered_docs[:5]:
                    response += doc.page_content.strip() + "\n\n"
            else:
                response = f"I couldn't find any institutions with assets over ${threshold/1_000_000_000:.1f}B in the current data."
        
        else:
            response = "Here are some relevant financial institutions based on your query:\n\n"
            for doc in docs[:3]:
                response += doc.page_content.strip() + "\n\n"
        
        return {
            'answer': response,
            'relevant_documents': [doc.page_content for doc in docs],
            'metadata': [doc.metadata for doc in docs]
        }
    
    def analyze_trends(self, question: str) -> Dict[str, Any]:
        """
        Analyze trends in financial institution data based on natural language query
        """
        # TODO: Implement trend analysis using time series data
        pass 