const assert = require('assert');
const app = require('../../src/app');

describe('App Tests', () => {
    it('should return a greeting message', () => {
        const result = app.greet('World');
        assert.strictEqual(result, 'Hello, World!');
    });

    it('should add two numbers correctly', () => {
        const result = app.add(2, 3);
        assert.strictEqual(result, 5);
    });

    // Add more tests as needed
});