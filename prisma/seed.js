const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();

const stocks = [
  // Banks
  { ticker: "HBL", name: "Habib Bank Limited", sector: "Commercial Banks", marketCap: "Large" },
  { ticker: "UBL", name: "United Bank Limited", sector: "Commercial Banks", marketCap: "Large" },
  { ticker: "MCB", name: "MCB Bank Limited", sector: "Commercial Banks", marketCap: "Large" },
  { ticker: "BAFL", name: "Bank Alfalah Limited", sector: "Commercial Banks", marketCap: "Mid" },
  { ticker: "MEBL", name: "Meezan Bank Limited", sector: "Commercial Banks", marketCap: "Large" },
  { ticker: "NBP", name: "National Bank of Pakistan", sector: "Commercial Banks", marketCap: "Mid" },

  // Oil & Gas
  { ticker: "OGDC", name: "Oil & Gas Development Company", sector: "Oil & Gas Exploration", marketCap: "Large" },
  { ticker: "PPL", name: "Pakistan Petroleum Limited", sector: "Oil & Gas Exploration", marketCap: "Large" },
  { ticker: "PSO", name: "Pakistan State Oil", sector: "Oil & Gas Marketing", marketCap: "Mid" },
  { ticker: "MARI", name: "Mari Petroleum Company", sector: "Oil & Gas Exploration", marketCap: "Large" },

  // Cement
  { ticker: "LUCK", name: "Lucky Cement Limited", sector: "Cement", marketCap: "Large" },
  { ticker: "DGKC", name: "DG Khan Cement Company", sector: "Cement", marketCap: "Mid" },
  { ticker: "MLCF", name: "Maple Leaf Cement", sector: "Cement", marketCap: "Mid" },
  { ticker: "PIOC", name: "Pioneer Cement Limited", sector: "Cement", marketCap: "Small" },

  // Fertilizer
  { ticker: "ENGRO", name: "Engro Corporation", sector: "Fertilizer", marketCap: "Large" },
  { ticker: "FFC", name: "Fauji Fertilizer Company", sector: "Fertilizer", marketCap: "Large" },
  { ticker: "EFERT", name: "Engro Fertilizers Limited", sector: "Fertilizer", marketCap: "Mid" },

  // Pharma
  { ticker: "SEARL", name: "The Searle Company Limited", sector: "Pharmaceuticals", marketCap: "Mid" },
  { ticker: "AGP", name: "AGP Limited", sector: "Pharmaceuticals", marketCap: "Small" },

  // Technology
  { ticker: "SYS", name: "Systems Limited", sector: "Technology & Communication", marketCap: "Mid" },
  { ticker: "TRG", name: "TRG Pakistan Limited", sector: "Technology & Communication", marketCap: "Mid" },
  { ticker: "NETSOL", name: "NetSol Technologies", sector: "Technology & Communication", marketCap: "Small" },

  // Power
  { ticker: "HUBC", name: "Hub Power Company", sector: "Power Generation & Distribution", marketCap: "Large" },
  { ticker: "KEL", name: "K-Electric Limited", sector: "Power Generation & Distribution", marketCap: "Mid" },

  // Automobile
  { ticker: "INDU", name: "Indus Motor Company", sector: "Automobile Assembler", marketCap: "Mid" },
  { ticker: "PSMC", name: "Pak Suzuki Motor Company", sector: "Automobile Assembler", marketCap: "Mid" },

  // Textile
  { ticker: "ILP", name: "Interloop Limited", sector: "Textile Composite", marketCap: "Mid" },

  // Tobacco
  { ticker: "PAKT", name: "Pakistan Tobacco Company", sector: "Tobacco", marketCap: "Mid" },

  // Food
  { ticker: "NESTLE", name: "Nestle Pakistan Limited", sector: "Food & Personal Care", marketCap: "Large" },
  { ticker: "FFL", name: "Friesland Campina Engro Pakistan", sector: "Food & Personal Care", marketCap: "Small" },
];

async function main() {
  console.log("Seeding PSX stocks...");

  for (const stock of stocks) {
    await prisma.stock.upsert({
      where: { ticker: stock.ticker },
      update: {},
      create: stock,
    });
  }

  console.log(`Seeded ${stocks.length} stocks.`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
