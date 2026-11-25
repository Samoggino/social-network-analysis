import java.awt.Color;
import java.awt.Font;
import java.io.File;

import org.gephi.graph.api.GraphController;
import org.gephi.graph.api.GraphModel;
import org.gephi.graph.api.Node;
import org.gephi.io.exporter.api.ExportController;
import org.gephi.io.exporter.preview.PNGExporter;
import org.gephi.io.importer.api.Container;
import org.gephi.io.importer.api.ImportController;
import org.gephi.io.processor.plugin.DefaultProcessor;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2Builder;
import org.gephi.preview.api.PreviewController;
import org.gephi.preview.api.PreviewProperties;
import org.gephi.preview.api.PreviewProperty;
import org.gephi.preview.types.DependantColor;
import org.gephi.preview.types.DependantOriginalColor;
import org.gephi.preview.types.EdgeColor;
import org.gephi.project.api.ProjectController;
import org.gephi.project.api.Workspace;
import org.openide.util.Lookup;

/**
 * Renders the report figures with the Gephi toolkit of the installed Gephi
 * (no GUI): ForceAtlas2 layout, then Preview export to PNG and PDF.
 * Colours, sizes and edge weights come from the GEXF written by
 * make_report_graphs.py.
 *
 * Usage: java RenderReportGraphs out_dir graph.gexf...
 */
public class RenderReportGraphs {

    public static void main(String[] args) throws Exception {
        File outDir = new File(args[0]);
        ProjectController projects = Lookup.getDefault().lookup(ProjectController.class);
        ImportController importer = Lookup.getDefault().lookup(ImportController.class);
        PreviewController preview = Lookup.getDefault().lookup(PreviewController.class);
        ExportController exporter = Lookup.getDefault().lookup(ExportController.class);
        projects.newProject();

        for (int i = 1; i < args.length; i++) {
            File gexf = new File(args[i]);
            String name = gexf.getName().replace(".gexf", "");
            Workspace ws = projects.newWorkspace(projects.getCurrentProject());
            projects.openWorkspace(ws);

            Container container = importer.importFile(gexf);
            importer.process(container, new DefaultProcessor(), ws);
            GraphModel model = Lookup.getDefault().lookup(GraphController.class).getGraphModel(ws);

            // The importer rescales viz:size; restore the sizes written by make_report_graphs.py.
            for (Node n : model.getGraph().getNodes()) {
                n.setSize(((Number) n.getAttribute("vsize")).floatValue());
            }

            boolean sparse = name.startsWith("reciprocal");
            ForceAtlas2 fa2 = new ForceAtlas2Builder().buildLayout();
            fa2.setGraphModel(model);
            fa2.resetPropertiesValues();
            fa2.setThreadsCount(1);              // deterministic
            fa2.setBarnesHutOptimize(false);
            fa2.setLinLogMode(!sparse);          // LinLog separates clusters
            fa2.setEdgeWeightInfluence(1.0);
            fa2.setScalingRatio(sparse ? 80.0 : 25.0);
            fa2.setGravity(sparse ? 0.05 : 1.0);
            fa2.setStrongGravityMode(sparse);   // keeps the small components together
            fa2.setAdjustSizes(false);
            fa2.initAlgo();
            for (int it = 0; it < 3000 && fa2.canAlgo(); it++) {
                if (it == 2500) fa2.setAdjustSizes(true);   // final pass: no overlaps
                fa2.goAlgo();
            }
            fa2.endAlgo();

            PreviewProperties p = preview.getModel(ws).getProperties();
            p.putValue(PreviewProperty.BACKGROUND_COLOR, Color.WHITE);
            p.putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
            p.putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
            p.putValue(PreviewProperty.NODE_LABEL_FONT, new Font("DejaVu Sans", Font.BOLD, sparse ? 5 : 9));
            p.putValue(PreviewProperty.NODE_LABEL_COLOR, new DependantOriginalColor(Color.BLACK));
            p.putValue(PreviewProperty.NODE_LABEL_OUTLINE_SIZE, 3f);
            p.putValue(PreviewProperty.NODE_LABEL_OUTLINE_COLOR, new DependantColor(Color.WHITE));
            p.putValue(PreviewProperty.NODE_LABEL_OUTLINE_OPACITY, 80f);
            p.putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.6f);
            p.putValue(PreviewProperty.EDGE_CURVED, Boolean.TRUE);
            p.putValue(PreviewProperty.EDGE_COLOR, new EdgeColor(EdgeColor.Mode.ORIGINAL));
            p.putValue(PreviewProperty.EDGE_OPACITY, 100f);
            p.putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
            p.putValue(PreviewProperty.EDGE_RESCALE_WEIGHT_MIN, sparse ? 1.0f : 0.8f);
            p.putValue(PreviewProperty.EDGE_RESCALE_WEIGHT_MAX, sparse ? 4f : 5f);
            p.putValue(PreviewProperty.ARROW_SIZE, 1.5f);
            p.putValue(PreviewProperty.MARGIN, 4f);
            preview.refreshPreview(ws);

            PNGExporter png = (PNGExporter) exporter.getExporter("png");
            png.setWorkspace(ws);
            png.setWidth(2400);
            png.setHeight(2400);
            png.setTransparentBackground(false);
            exporter.exportFile(new File(outDir, name + ".png"), png);
            exporter.exportFile(new File(outDir, name + ".pdf"), ws);
            exporter.exportFile(new File(outDir, name + ".svg"), ws);   // flags are added on this
            System.out.println(name + ": " + model.getGraph().getNodeCount() + " nodes, "
                    + model.getGraph().getEdgeCount() + " edges");
        }
        System.exit(0);
    }
}
