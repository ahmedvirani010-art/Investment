import { render, screen } from '@testing-library/react';
import Home from '../page';

// Mock next/image
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...props} />;
  },
}));

describe('Home Page', () => {
  it('should render the main heading', () => {
    render(<Home />);
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('To get started, edit the page.tsx file.');
  });

  it('should render the Next.js logo', () => {
    render(<Home />);
    const logo = screen.getByAltText('Next.js logo');
    expect(logo).toBeInTheDocument();
  });

  it('should render the description text', () => {
    render(<Home />);
    expect(screen.getByText(/Looking for a starting point/i)).toBeInTheDocument();
  });

  it('should render Templates link', () => {
    render(<Home />);
    const templatesLink = screen.getByRole('link', { name: /templates/i });
    expect(templatesLink).toBeInTheDocument();
    expect(templatesLink).toHaveAttribute('href', expect.stringContaining('vercel.com/templates'));
  });

  it('should render Learning link', () => {
    render(<Home />);
    const learningLink = screen.getByRole('link', { name: /learning/i });
    expect(learningLink).toBeInTheDocument();
    expect(learningLink).toHaveAttribute('href', expect.stringContaining('nextjs.org/learn'));
  });

  it('should render Deploy Now button', () => {
    render(<Home />);
    const deployButton = screen.getByRole('link', { name: /deploy now/i });
    expect(deployButton).toBeInTheDocument();
  });

  it('should render Documentation button', () => {
    render(<Home />);
    const docsButton = screen.getByRole('link', { name: /documentation/i });
    expect(docsButton).toBeInTheDocument();
  });

  it('should have proper semantic structure', () => {
    const { container } = render(<Home />);
    const main = container.querySelector('main');
    expect(main).toBeInTheDocument();
  });
});
