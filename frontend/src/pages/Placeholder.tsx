import { Card, PageHeader } from '../components/ui'

/** Stands in for a screen that has a route but is not built yet. */
export function Placeholder({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <Card className="p-10 text-sm text-muted">This screen is next on the build list.</Card>
    </>
  )
}
