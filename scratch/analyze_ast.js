const fs = require('fs');
const acorn = require('../electron_dashboard/node_modules/acorn');

const code = fs.readFileSync('./electron_dashboard/ui_dashboard_common.js', 'utf8');
const ast = acorn.parse(code, { ecmaVersion: 2020 });

// Find function declarations and see if they are at the top level
console.log("Top-level elements:");
ast.body.forEach(node => {
    if (node.type === 'FunctionDeclaration') {
        console.log(`- Function: ${node.id.name} (Lines: ${code.slice(0, node.start).split('\n').length} - ${code.slice(0, node.end).split('\n').length})`);
    } else if (node.type === 'VariableDeclaration') {
        node.declarations.forEach(dec => {
            console.log(`- Variable: ${dec.id.name} (Lines: ${code.slice(0, node.start).split('\n').length})`);
        });
    } else if (node.type === 'ExpressionStatement') {
        console.log(`- Expression: ${code.slice(node.start, node.end).substring(0, 50)}... (Line: ${code.slice(0, node.start).split('\n').length})`);
    } else {
        console.log(`- Other: ${node.type} (Line: ${code.slice(0, node.start).split('\n').length})`);
    }
});
