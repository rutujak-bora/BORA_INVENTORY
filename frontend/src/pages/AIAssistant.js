import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, MessageSquare, Search, TrendingUp, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import axios from '@/utils/api';
import { toast } from 'sonner';

const AIAssistant = () => {
    const [messages, setMessages] = useState([
        { 
            role: 'assistant', 
            text: "Hello! I'm your Bora DMS Assistant. I can help you find details about Invoices, Purchase Orders, or check SKU stock levels. What can I help you with today?" 
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
        setLoading(true);

        try {
            // Prepare history for API (converts state history to Gemini format)
            const history = messages.map(m => ({
                role: m.role === 'assistant' ? 'model' : 'user',
                parts: [{ text: m.text }]
            }));

            const response = await axios.post('/chat', {
                message: userMessage,
                history: history.slice(-10) // Send last 10 messages for context
            });

            if (response.data.error) {
                toast.error("AI Assistant is offline. Please check API settings.");
                setMessages(prev => [...prev, { 
                    role: 'assistant', 
                    text: response.data.text || "I'm sorry, I'm having trouble connecting to my brain right now." 
                }]);
            } else {
                setMessages(prev => [...prev, { role: 'assistant', text: response.data.text }]);
            }
        } catch (error) {
            console.error("Chat Error:", error);
            toast.error("Failed to connect to assistant");
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                text: "I encountered an error while trying to reach the server. Please check your connection." 
            }]);
        } finally {
            setLoading(false);
        }
    };

    const suggestedQueries = [
        { label: "Check Stock", query: "What is the stock level for [SKU Name]?", icon: TrendingUp },
        { label: "Find by Company", query: "Find documents for [Company Name]", icon: Search },
        { label: "Category Summary", query: "What is the total stock for category [Category]?", icon: MessageSquare },
        { label: "Pending PIs", query: "Show me all pending Proforma Invoices", icon: Loader2 },
        { label: "Recent Activity", query: "Show me recent inward and outward movements", icon: TrendingUp },
    ];

    return (
        <div className="flex flex-col h-[calc(100vh-120px)] max-w-5xl mx-auto space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
                        <Bot className="text-blue-600" size={32} />
                        Bora Assistant
                    </h1>
                    <p className="text-slate-500">Intelligent data query and stock tracking</p>
                </div>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    Live with Gemini 1.5
                </Badge>
            </div>

            <Card className="flex-1 flex flex-col overflow-hidden border-slate-200 shadow-xl bg-white/50 backdrop-blur-sm">
                <CardHeader className="border-b bg-slate-50/50 flex flex-row items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                        <MessageSquare size={18} className="text-blue-600" />
                        <CardTitle className="text-sm font-medium">Chat Conversation</CardTitle>
                    </div>
                </CardHeader>
                
                <CardContent className="flex-1 overflow-hidden p-0 flex flex-col">
                    <ScrollArea className="flex-1 p-6">
                        <div className="space-y-6">
                            {messages.map((m, i) => (
                                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`flex gap-3 max-w-[80%] ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm ${
                                            m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-blue-600'
                                        }`}>
                                            {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                                        </div>
                                        <div className={`p-4 rounded-2xl shadow-sm ${
                                            m.role === 'user' 
                                            ? 'bg-blue-600 text-white rounded-tr-none' 
                                            : 'bg-white border border-slate-100 text-slate-800 rounded-tl-none'
                                        }`}>
                                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="flex justify-start">
                                    <div className="flex gap-3 items-center text-slate-400">
                                        <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center">
                                            <Bot size={16} />
                                        </div>
                                        <div className="flex gap-1 animate-pulse">
                                            <span className="w-1.5 h-1.5 bg-slate-300 rounded-full"></span>
                                            <span className="w-1.5 h-1.5 bg-slate-300 rounded-full"></span>
                                            <span className="w-1.5 h-1.5 bg-slate-300 rounded-full"></span>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={scrollRef} />
                        </div>
                    </ScrollArea>

                    {/* Quick Queries */}
                    {messages.length < 3 && (
                        <div className="px-6 py-4 flex flex-wrap gap-2 animate-in fade-in slide-in-from-bottom-2 duration-700">
                            {suggestedQueries.map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => setInput(q.query)}
                                    className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-medium hover:bg-blue-100 transition-colors"
                                >
                                    <q.icon size={12} />
                                    {q.label}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Input Area */}
                    <div className="p-4 border-t bg-white">
                        <form onSubmit={handleSendMessage} className="flex gap-3">
                            <Input
                                placeholder="Ask me about PIs, POs, or SKU levels..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                className="flex-1 h-12 border-slate-200 focus:ring-blue-500"
                                disabled={loading}
                            />
                            <Button 
                                type="submit" 
                                className="h-12 w-12 rounded-xl bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all active:scale-95"
                                disabled={loading || !input.trim()}
                            >
                                {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                            </Button>
                        </form>
                        <p className="mt-2 text-[10px] text-center text-slate-400 flex items-center justify-center gap-1">
                            <HelpCircle size={10} />
                            Bora Assistant can make mistakes. Verify important stock data in the summary module.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default AIAssistant;
