import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders the header', () => {
    render(<App />);
    expect(screen.getByText('Financial Manager')).toBeInTheDocument();
  });

  it('renders the tax form', () => {
    render(<App />);
    expect(screen.getByLabelText('Gross Income')).toBeInTheDocument();
    expect(screen.getByLabelText('Filing Status')).toBeInTheDocument();
    expect(screen.getByLabelText('Tax Year')).toBeInTheDocument();
  });

  it('renders the placeholder when no results', () => {
    render(<App />);
    expect(screen.getByText('Enter your information')).toBeInTheDocument();
  });

  it('has a calculate button', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: /calculate tax/i })).toBeInTheDocument();
  });
});
