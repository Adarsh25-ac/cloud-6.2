-- Recipe Database Schema & Initial Data

CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    prep_time INTEGER NOT NULL, -- in minutes
    cook_time INTEGER NOT NULL, -- in minutes
    servings INTEGER NOT NULL DEFAULT 2,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL,
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial sample recipes
INSERT INTO recipes (title, category, prep_time, cook_time, servings, ingredients, instructions, image_url)
VALUES 
(
    'Classic Margherita Pizza',
    'Italian',
    20,
    15,
    3,
    '• 250g Pizza dough\n• 1/2 cup San Marzano tomato sauce\n• 150g Fresh mozzarella cheese (sliced)\n• Fresh basil leaves\n• 1 tbsp Extra virgin olive oil\n• Pinch of sea salt',
    '1. Preheat oven to 250°C (480°F) or highest setting with a pizza stone.\n2. Roll out the pizza dough on a floured surface to 10-12 inches.\n3. Spread tomato sauce evenly leaving a 1/2-inch border.\n4. Arrange mozzarella slices over the sauce.\n5. Bake for 10-12 minutes until crust is golden and cheese bubbles.\n6. Garnish with fresh basil, drizzle olive oil, and sprinkle sea salt before serving.',
    'https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?auto=format&fit=crop&w=600&q=80'
),
(
    'Creamy Garlic Butter Chicken',
    'Dinner',
    15,
    20,
    4,
    '• 500g Chicken breast (filleted)\n• 4 cloves Garlic (minced)\n• 1 cup Heavy cream\n• 1/2 cup Chicken broth\n• 2 tbsp Butter\n• 1 cup Baby spinach\n• 1/2 cup Grated parmesan\n• Salt & black pepper to taste',
    '1. Season chicken fillets with salt and pepper.\n2. Melt butter in a large skillet over medium-high heat and sear chicken for 5-6 mins per side until golden; set aside.\n3. In the same pan, sauté minced garlic for 1 minute.\n4. Pour in chicken broth and heavy cream; simmer for 3 minutes.\n5. Stir in parmesan cheese and spinach until wilted.\n6. Return chicken to the skillet and spoon sauce over top. Serve warm.',
    'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=600&q=80'
),
(
    'Avocado & Poached Egg Toast',
    'Breakfast',
    10,
    5,
    2,
    '• 2 slices Sourdough bread\n• 1 ripe Avocado\n• 2 Fresh eggs\n• 1 tbsp Lemon juice\n• Red pepper flakes\n• Salt and freshly ground black pepper',
    '1. Toast sourdough slices until golden and crisp.\n2. Mash avocado in a bowl with lemon juice, salt, and pepper.\n3. Bring a small pot of water to a gentle simmer, create a whirlpool, and slide cracked egg into the center. Poach for 3-4 minutes.\n4. Spread mashed avocado onto toast slices.\n5. Top each toast with a poached egg and sprinkle chili flakes.',
    'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=600&q=80'
);
