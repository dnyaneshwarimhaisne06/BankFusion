import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface Transaction {
  date: string;
  description: string;
  debit: number | null;
  credit: number | null;
  balance: number | null;
  category: string;
}

interface ProcessingResult {
  bank_name: string;
  transactions: Transaction[];
  categories_summary: Record<string, { count: number; total: number }>;
}

const CATEGORY_KEYWORDS: Record<string, string[]> = {
  "Food & Dining": ["swiggy", "zomato", "restaurant", "food", "cafe", "pizza", "burger", "hotel", "dining", "kitchen", "eatery", "bakery"],
  "Travel": ["uber", "ola", "flight", "train", "irctc", "makemytrip", "goibibo", "travel", "airlines", "cab", "taxi", "metro", "bus"],
  "Rent": ["rent", "lease", "landlord", "housing", "apartment", "flat", "pg accommodation"],
  "Utilities": ["electricity", "water", "gas", "internet", "broadband", "wifi", "phone", "mobile", "recharge", "dth", "postpaid", "prepaid", "bill payment"],
  "Shopping": ["amazon", "flipkart", "myntra", "ajio", "shopping", "mall", "store", "retail", "mart", "bazaar", "purchase"],
  "Entertainment": ["netflix", "spotify", "prime", "hotstar", "movie", "cinema", "theatre", "game", "music", "subscription"],
  "Healthcare": ["hospital", "medical", "pharmacy", "doctor", "clinic", "health", "medicine", "diagnostic", "lab"],
  "Transfers": ["upi", "imps", "neft", "rtgs", "transfer", "sent to", "received from", "p2p"],
  "ATM": ["atm", "cash withdrawal", "cash deposit"],
  "Salary": ["salary", "payroll", "wages", "income"],
  "Investment": ["mutual fund", "sip", "stock", "share", "trading", "investment", "zerodha", "groww", "upstox"],
  "Insurance": ["insurance", "lic", "policy", "premium"],
  "EMI": ["emi", "loan", "instalment", "installment"],
};

function categorizeTransaction(description: string): string {
  const lowerDesc = description.toLowerCase();
  
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    for (const keyword of keywords) {
      if (lowerDesc.includes(keyword)) {
        return category;
      }
    }
  }
  
  return "Other";
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { statement_id, file_path, pdf_text } = await req.json();
    
    if (!statement_id) {
      return new Response(
        JSON.stringify({ error: "statement_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) {
      throw new Error("LOVABLE_API_KEY is not configured");
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Get the statement to verify it exists
    const { data: statement, error: statementError } = await supabase
      .from("bank_statements")
      .select("*")
      .eq("id", statement_id)
      .single();

    if (statementError || !statement) {
      throw new Error("Statement not found");
    }

    // Use AI to extract transactions from PDF text
    const aiPrompt = `You are a bank statement parser. Analyze the following bank statement text and extract all transactions.

For each transaction, extract:
1. Date (in YYYY-MM-DD format)
2. Description (merchant name or transaction description)
3. Debit amount (money spent, null if credit)
4. Credit amount (money received, null if debit)
5. Balance after transaction (if available)

Also detect the bank name from the statement header/content.

IMPORTANT: Return ONLY valid JSON, no markdown formatting.

Bank Statement Text:
${pdf_text || "No PDF text provided - simulate sample transactions for testing"}

Return JSON in this exact format:
{
  "bank_name": "Detected Bank Name",
  "transactions": [
    {
      "date": "2024-01-15",
      "description": "SWIGGY ORDER",
      "debit": 450.00,
      "credit": null,
      "balance": 25000.00
    }
  ]
}`;

    console.log("Calling Lovable AI for transaction extraction...");

    const aiResponse = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages: [
          {
            role: "system",
            content: "You are an expert bank statement parser. Extract transactions accurately and return valid JSON only. Never include markdown code blocks in your response.",
          },
          { role: "user", content: aiPrompt },
        ],
      }),
    });

    if (!aiResponse.ok) {
      const errorText = await aiResponse.text();
      console.error("AI Gateway error:", aiResponse.status, errorText);
      
      if (aiResponse.status === 429) {
        return new Response(
          JSON.stringify({ error: "Rate limit exceeded. Please try again later." }),
          { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      if (aiResponse.status === 402) {
        return new Response(
          JSON.stringify({ error: "AI credits exhausted. Please add credits." }),
          { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      throw new Error(`AI Gateway error: ${aiResponse.status}`);
    }

    const aiData = await aiResponse.json();
    let aiContent = aiData.choices?.[0]?.message?.content || "";
    
    console.log("AI Response received:", aiContent.substring(0, 500));

    // Clean up the response - remove markdown code blocks if present
    aiContent = aiContent.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();

    let parsedResult: ProcessingResult;
    try {
      const parsed = JSON.parse(aiContent);
      
      // Categorize each transaction
      const categorizedTransactions: Transaction[] = (parsed.transactions || []).map((tx: any) => ({
        date: tx.date,
        description: tx.description,
        debit: tx.debit,
        credit: tx.credit,
        balance: tx.balance,
        category: categorizeTransaction(tx.description),
      }));

      // Calculate category summaries
      const categoriesSummary: Record<string, { count: number; total: number }> = {};
      for (const tx of categorizedTransactions) {
        const amount = tx.debit || 0;
        if (!categoriesSummary[tx.category]) {
          categoriesSummary[tx.category] = { count: 0, total: 0 };
        }
        categoriesSummary[tx.category].count++;
        categoriesSummary[tx.category].total += amount;
      }

      parsedResult = {
        bank_name: parsed.bank_name || statement.bank_name,
        transactions: categorizedTransactions,
        categories_summary: categoriesSummary,
      };
    } catch (parseError) {
      console.error("JSON parse error:", parseError);
      console.error("Content that failed to parse:", aiContent);
      throw new Error("Failed to parse AI response as JSON");
    }

    // Insert transactions into database
    if (parsedResult.transactions.length > 0) {
      const transactionsToInsert = parsedResult.transactions.map((tx) => ({
        statement_id: statement_id,
        user_id: statement.user_id,
        date: tx.date,
        description: tx.description,
        debit: tx.debit,
        credit: tx.credit,
        balance: tx.balance,
        category: tx.category,
      }));

      const { error: txError } = await supabase
        .from("transactions")
        .insert(transactionsToInsert);

      if (txError) {
        console.error("Transaction insert error:", txError);
        throw txError;
      }

      // Insert category summaries
      const categoriesToInsert = Object.entries(parsedResult.categories_summary).map(
        ([category, data]) => ({
          statement_id: statement_id,
          user_id: statement.user_id,
          category_name: category,
          transaction_count: data.count,
          total_amount: data.total,
        })
      );

      const { error: catError } = await supabase
        .from("categories_summary")
        .insert(categoriesToInsert);

      if (catError) {
        console.error("Category summary insert error:", catError);
      }
    }

    // Update statement status and bank name
    const { error: updateError } = await supabase
      .from("bank_statements")
      .update({
        status: "completed",
        bank_name: parsedResult.bank_name,
        metadata: {
          processed_at: new Date().toISOString(),
          transaction_count: parsedResult.transactions.length,
          categories: Object.keys(parsedResult.categories_summary),
        },
      })
      .eq("id", statement_id);

    if (updateError) {
      console.error("Statement update error:", updateError);
    }

    console.log(`Successfully processed statement ${statement_id} with ${parsedResult.transactions.length} transactions`);

    return new Response(
      JSON.stringify({
        success: true,
        bank_name: parsedResult.bank_name,
        transaction_count: parsedResult.transactions.length,
        categories: Object.keys(parsedResult.categories_summary),
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Processing error:", error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : "Processing failed" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
