import java.io.File;
import java.awt.Font;
import java.util.ArrayList;
import java.util.List;

import org.gephi.io.importer.api.Container;
import org.gephi.io.importer.api.EdgeDirectionDefault;
import org.gephi.io.importer.api.ImportController;
import org.gephi.io.processor.plugin.DefaultProcessor;
import org.gephi.preview.api.PreviewController;
import org.gephi.preview.api.PreviewProperties;
import org.gephi.preview.api.PreviewProperty;
import org.gephi.preview.types.EdgeColor;
import org.gephi.project.api.Project;
import org.gephi.project.api.ProjectController;
import org.gephi.project.api.Workspace;
import org.openide.util.Lookup;

/**
 * Builds a Gephi project (.gephi) with one workspace per GEXF file, using the
 * libraries of the installed Gephi (no GUI).
 *
 * Usage: java MakeGephiProject out.gephi graph1.gexf [graph2.gexf ...]
 * The workspace name is the GEXF file name without "_styled.gexf".
 *
 * Positions, colours and sizes come from the GEXF "viz" data written by
 * style_gexf.py; here we only add the Preview settings that a GEXF cannot
 * store: node labels, straight edges coloured as in the file, arrows.
 */
public class MakeGephiProject {

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: MakeGephiProject out.gephi graph.gexf...");
            System.exit(2);
        }
        File out = new File(args[0]).getAbsoluteFile();

        ProjectController projects = Lookup.getDefault().lookup(ProjectController.class);
        ImportController importer = Lookup.getDefault().lookup(ImportController.class);
        PreviewController preview = Lookup.getDefault().lookup(PreviewController.class);

        Project project = projects.newProject();
        projects.renameProject(project, out.getName().replace(".gephi", ""));
        Workspace first = projects.getCurrentWorkspace();

        List<String> names = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            File gexf = new File(args[i]);
            Workspace workspace = (i == 1) ? first : projects.newWorkspace(project);

            Container container = importer.importFile(gexf);
            container.getLoader().setEdgeDefault(EdgeDirectionDefault.DIRECTED);
            importer.process(container, new DefaultProcessor(), workspace);

            String name = gexf.getName().replace("_styled.gexf", "").replace(".gexf", "");
            projects.renameWorkspace(workspace, name);
            names.add(name);

            PreviewProperties props = preview.getModel(workspace).getProperties();
            props.putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
            props.putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
            props.putValue(PreviewProperty.NODE_LABEL_FONT, new Font("SansSerif", Font.BOLD, 10));
            props.putValue(PreviewProperty.EDGE_CURVED, Boolean.FALSE);
            props.putValue(PreviewProperty.EDGE_COLOR, new EdgeColor(EdgeColor.Mode.ORIGINAL));
            props.putValue(PreviewProperty.EDGE_OPACITY, 60f);
            props.putValue(PreviewProperty.EDGE_RESCALE_WEIGHT, Boolean.TRUE);
            props.putValue(PreviewProperty.EDGE_RESCALE_WEIGHT_MIN, 0.3f);
            props.putValue(PreviewProperty.EDGE_RESCALE_WEIGHT_MAX, 5f);
            props.putValue(PreviewProperty.ARROW_SIZE, 3f);
        }

        projects.openWorkspace(first);
        projects.saveProject(project, out);
        System.out.println(out + ": " + names.size() + " workspaces " + names);
        System.exit(0);
    }
}
